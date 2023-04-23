import SimpleITK
import psutil
from mpire import WorkerPool
from enum import IntEnum
import pandas as pd


class Metric(IntEnum):
    LABEL = 0
    DICE = 1
    JACCARD = 2
    VOLUME_SIMILARITY = 3
    HAUSDORFF_DISTANCE = 4
    INTENSITY_TOTAL = 5
    INTENSITY_MEAN = 6
    INTENSITY_STD = 7


def split_metrics(list_of_metrics):
    """
    Splits a list of metrics into multiple lists , each containing a designated metric
    :param list_of_metrics:
    :return split_list_of_metrics: split metrics list
    """
    split_list_of_metrics = list(map(list, zip(*list_of_metrics)))
    return split_list_of_metrics


def append_column_stats(data: list, row_names: list):
    data_df = pd.DataFrame(data, index=row_names, columns=list(range(1, len(data[0]) + 1)))

    data_means = list(data_df.mean(numeric_only=True))
    data_std = list(data_df.std(numeric_only=True))
    data_total = list(data_df.sum(numeric_only=True))

    data_mean_df = pd.DataFrame([data_means], index=["Mean"], columns=list(range(1, len(data_means) + 1)))
    data_std_df = pd.DataFrame([data_std], index=["STD"], columns=list(range(1, len(data_std) + 1)))
    data_total_df = pd.DataFrame([data_total], index=["Total"], columns=list(range(1, len(data_total) + 1)))

    data_combined_df = pd.concat([data_df, data_mean_df, data_std_df, data_total_df])
    return data_combined_df


def write_metrics(metrics_file_path, all_metrics, rows):
    with pd.ExcelWriter(metrics_file_path) as writer:
        for metric_index in Metric:
            current_metric_values = [metric[metric_index] for metric in all_metrics]
            (append_column_stats(current_metric_values, rows)).to_excel(writer, sheet_name=str(metric_index))


def evaluate_label(image_tuple: tuple, label: int) -> list:
    """
    :param image_tuple: SimpleITK image Tuple, containing two images to be compared
    :param label: Desired label to analyze
    :return label_parameters: List of retrieved Metrics for specified label, containing:
            0: label
            1: DICE
            2: Jaccard
            3: Volume Similarity
            4: Hausdorff Distance
            5: Hausdorff Distance[MedPy]
            6: ASSD [MedPy]
            7: DICE [MedPy]
    """

    # Extract Images out of tuple
    reference_image, registered_image, intensity_image = image_tuple

    # Create and execute the LabelOverlapMeasures Filter to calculate the metrics between every label of the images
    overlap_measures_filter = SimpleITK.LabelOverlapMeasuresImageFilter()
    overlap_measures_filter.Execute(reference_image, registered_image)

    # Get Overlap Measurements
    d = overlap_measures_filter.GetDiceCoefficient(label)
    j = overlap_measures_filter.GetJaccardCoefficient(label)
    vs = overlap_measures_filter.GetVolumeSimilarity(label)

    # Extract desired Label with Thresholding
    single_label_reference = SimpleITK.Threshold(reference_image, lower=label, upper=label)
    single_label_compare = SimpleITK.Threshold(registered_image, lower=label, upper=label)

    # Get Distance Measurements from SimpleITK
    hausdorff_distance_filter = SimpleITK.HausdorffDistanceImageFilter()
    hausdorff_distance_filter.Execute(single_label_reference, single_label_compare)
    hd = hausdorff_distance_filter.GetHausdorffDistance()

    # Get Intensity values
    intensity_statistics = SimpleITK.LabelIntensityStatisticsImageFilter()
    intensity_statistics.Execute(registered_image, intensity_image)
    intensity_mean = intensity_statistics.GetMean(label)
    intensity_STD = intensity_statistics.GetStandardDeviation(label)
    intensity_total = intensity_statistics.GetSum(label)


    # Print for Logging
    print("   Label " + str(label) +
          ": DICE: " + str(d) +
          " | Jaccard: " + str(j) +
          " | Volume Similarity: " + str(vs) +
          " | Hausdorff: " + str(hd) +
          " | Intensity [Total]: " + str(intensity_total) +
          " | Intensity [Mean]: " + str(intensity_mean) +
          " | Intensity [STD]: " + str(intensity_STD))

    # Build List and return
    label_parameters = [label, d, j, vs, hd,
                        intensity_total, intensity_mean, intensity_STD]
    return label_parameters


def evaluate_all_labels_MP(reference_image, registered_image, intensity_image):
    """
    Evaluates registration results of all labels of reference_image and registered_image multithreaded
    :return metric_data_list: List of retrieved Metrics for all labels, containing:
    :param reference_image: SimpleITK reference image
    :param registered_image: SimpleITK image to be compared
    :param intensity_image: SimpleITK image for intensity evaluation
    """

    # Get number of labels
    cc = SimpleITK.ConnectedComponent(reference_image)
    stats = SimpleITK.LabelIntensityStatisticsImageFilter()
    stats.Execute(reference_image, cc)

    # Create a shared object to use by multithreaded function
    shared_objects = (reference_image, registered_image, intensity_image)

    # Determine number of cores and adjust number of concurrent jobs
    core_number = psutil.cpu_count()
    jobs = 1 #int(core_number / 8)
    print("   [Label Evaluation] Available Threads: " + str(core_number) + " - Process will use " + str(jobs))

    with WorkerPool(n_jobs=jobs, shared_objects=shared_objects) as pool:
        label_parameters = pool.map(evaluate_label, stats.GetLabels())

    metric_data_list = split_metrics(label_parameters)
    return metric_data_list


def evaluate_all_labels_ST(reference_image, registered_image):
    """
    Evaluates registration results of all labels of reference_image and registered_image singlehreaded
    :param reference_image: SimpleITK reference image
    :param registered_image: SimpleITK image to be compared
    """

    # Empty lists for Metrics
    label_identifier = []
    dice = []
    jaccard = []
    volume_similarity = []
    hausdorff_distance = []
    hausdorff_distance_medpy = []
    obj_assd_medpy = []
    dice_medpy = []

    # Get number of labels
    cc = SimpleITK.ConnectedComponent(reference_image)
    stats = SimpleITK.LabelIntensityStatisticsImageFilter()
    stats.Execute(reference_image, cc)

    # create and execute the LabelOverlapMeasures Filter to calculate the metrics between every label of the images
    overlap_measures_filter = SimpleITK.LabelOverlapMeasuresImageFilter()
    overlap_measures_filter.Execute(reference_image, registered_image)

    # loop through all labels to get the dice coefficient
    for label in stats.GetLabels():
        d = overlap_measures_filter.GetDiceCoefficient(label)
        j = overlap_measures_filter.GetJaccardCoefficient(label)
        vs = overlap_measures_filter.GetVolumeSimilarity(label)

        # Extract desired Label with Thresholding
        single_label_reference = SimpleITK.Threshold(reference_image, lower=label, upper=label)
        single_label_compare = SimpleITK.Threshold(registered_image, lower=label, upper=label)

        # Get Distance Measurements from SimpleITK
        hausdorff_distance_filter = SimpleITK.HausdorffDistanceImageFilter()
        hausdorff_distance_filter.Execute(single_label_reference, single_label_compare)
        hd = hausdorff_distance_filter.GetHausdorffDistance()

        print("   Label " + str(label) +
              ": DICE: " + str(d) +
              " | Volume Similarity: " + str(vs) +
              " | Jaccard: " + str(j) +
              " | Hausdorff: " + str(hd))

        label_identifier.append(label)
        dice.append(d)
        jaccard.append(j)
        volume_similarity.append(vs)
        hausdorff_distance.append(hd)

    metric_data_list = [label_identifier, dice, jaccard, volume_similarity, hausdorff_distance,
                        hausdorff_distance_medpy, obj_assd_medpy, dice_medpy]
    return metric_data_list