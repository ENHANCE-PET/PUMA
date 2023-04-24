import SimpleITK
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
    print(f"  Label {label:3}: DICE: {d:.2f} "
          f"| Jaccard: {j:.2f} "
          f"| Volume Similarity: {vs:.2f} "
          f"| Hausdorff: {hd:.2f} "
          f"| Intensity [Total]: {intensity_total:.2f} "
          f"| Intensity [Mean]: {intensity_mean:.2f} "
          f"| Intensity [STD]: {intensity_STD:.2f}")

    # Build List and return
    label_parameters = [label, d, j, vs, hd, intensity_total, intensity_mean, intensity_STD]
    return label_parameters
