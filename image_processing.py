import SimpleITK


def reslice_identity(reference_image_path, image_path, output_image_path, is_label_image=False, center_images=False):
    resampler = SimpleITK.ResampleImageFilter()
    reference_image = SimpleITK.ReadImage(reference_image_path)
    resampler.SetReferenceImage(reference_image)

    if is_label_image:
        image = SimpleITK.ReadImage(image_path, SimpleITK.sitkUInt8)
        resampler.SetInterpolator(SimpleITK.sitkNearestNeighbor)
    else:
        image = SimpleITK.ReadImage(image_path)
        resampler.SetInterpolator(SimpleITK.sitkLinear)

    if center_images:
        center_transform = SimpleITK.CenteredTransformInitializer(reference_image, image,
                                                                  SimpleITK.Euler3DTransform(),
                                                                  SimpleITK.CenteredTransformInitializerFilter.GEOMETRY)
        resampler.SetTransform(center_transform)

    resampled_image = resampler.Execute(image)
    if output_image_path is not None:
        SimpleITK.WriteImage(resampled_image, output_image_path)
    return resampled_image
