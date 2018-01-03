import numpy as np
from scipy.ndimage import (gaussian_filter, sobel)


def gaussian_filter_2d(box, data, sigma_lat, sigma_lon):
    """Filters a 2D (lat x lon) data set with a Gaussian, correcting for
    the distortion from the geographic projection.

    :param box: instance of :py:class:`Box`.
    :param data: data set, dimensions should match ``box.shape``.
    :param sigma_lat: sigma lat in dimension of distance (e.g. km).
    :param sigma_lon: sigma lon in dimension of distance (e.g. km).
    :return: :py:class:`numpy.ndarray` with the same shape as input.
    """
    res_lat, res_lon = box.resolution
    s_lat = (sigma_lat / res_lat).m_as('')
    s_lon = (sigma_lat / res_lat).m_as('')

    outp = np.zeros_like(data)

    for i, lat_rad in enumerate(box.lat / 180 * np.pi):
        gaussian_filter(
            data[i, :],
            min(data.shape[1], s_lon / np.cos(lat_rad)),
            mode=['wrap'],
            output=outp[i, :])

    gaussian_filter(
        outp, [s_lat, 0.0], mode=['constant', 'wrap'], output=outp, cval=0)

    return outp


def gaussian_filter_3d(box, data, sigma_t, sigma_lat, sigma_lon):
    """Filters a 3D (time x lat x lon) data set with a Gaussian, correcting for
    the distortion from the geographic projection.

    :param box: instance of :py:class:`Box`.
    :param data: data set, dimensions should match ``box.shape``.
    :param sigma_t: sigma time in dimension of time (e.g. year).
    :param sigma_lat: sigma lat in dimension of distance (e.g. km).
    :param sigma_lon: sigma lon in dimension of distance (e.g. km).
    :return: :py:class:`numpy.ndarray` with the same shape as input.
    """

    res_t, res_lat, res_lon = box.resolution
    s_t = (sigma_t / res_t).m_as('')
    s_lat = (sigma_lat / res_lat).m_as('')
    s_lon = (sigma_lat / res_lat).m_as('')

    outp = np.zeros_like(data)
    for i, lat_rad in enumerate(box.lat / 180 * np.pi):
        gaussian_filter(
            data[:, i, :],
            min(data.shape[2], s_lon / np.cos(lat_rad)),
            mode=['reflect', 'wrap'],
            output=outp[:, i, :])

    gaussian_filter(
        outp, [s_t, s_lat, 0.0], mode=['reflect', 'reflect', 'wrap'],
        output=outp)

    return outp


def sobel_filter_2d(box, data, weight=None, physical=True):
    """Sobel filter in 2D (lat x lon). Effectively computes a derivative.
    This filter is normalised to return a rate of change per pixel, or
    if weights are given, the value is multiplied by the weight to obtain
    a unitless quantity of change over the given weight.

    :param box: :py:class:`Box` instance
    :param data: input data, :py:class:`numpy.ndarray` with same shape
        as ``box.shape``.
    :param weight: weight of each dimension in combining components into
        a vector magnitude; should have units corresponding those given
        by ``box.resolution``.
    :param physical: wether to correct for geometric projection, by dividing
        the derivative in the longitudinal direction by the cosine of the
        latitude."""
    if weight is None:
        y = [1/8, 1/8]
    else:
        y = [(1/8 * w / r).m_as('') for w, r in zip(weight, box.resolution)]

    sb = np.array([
        sobel(data, mode=['reflect', 'wrap'], axis=i) * y[i]
        for i in range(2)])

    if physical:
        sb[1, :, :] /= np.cos(box.lat / 180 * np.pi)[:, None]

    sb = np.r_[sb, np.ones_like(sb[0:1])]
    norm = np.sqrt((sb[:-1]**2).sum(axis=0))
    sb /= norm
    return sb


def sobel_filter_3d(box, data, weight=None, physical=True, variability=None):
    """Sobel filter in 3D (time x lat x lon). Effectively computes a
    derivative.  This filter is normalised to return a rate of change per
    pixel, or if weights are given, the value is multiplied by the weight to
    obtain a unitless quantity of change over the given weight.

    :param box: :py:class:`Box` instance
    :param data: input data, :py:class:`numpy.ndarray` with same shape
        as ``box.shape``.
    :param weight: weight of each dimension in combining components into
        a vector magnitude; should have units corresponding those given
        by ``box.resolution``.
    :param physical: wether to correct for geometric projection, by dividing
        the derivative in the longitudinal direction by the cosine of the
        latitude."""
    if weight is None:
        y = [1/16, 1/16, 1/16]
    else:
        y = [(1/16 * w / r).m_as('') for w, r in zip(weight, box.resolution)]

    sb = np.array([
        sobel(data, mode=['reflect', 'reflect', 'wrap'], axis=i) * y[i]
        for i in range(3)])

    if variability is not None:
        for i in range(3):
            sb[i] /= variability[i]

    if physical:
        sb[2, :, :, :] /= np.cos(box.lat / 180 * np.pi)[None, :, None]

    sb = np.r_[sb, np.ones_like(sb[0:1])]
    norm = np.sqrt((sb[:-1]**2).sum(axis=0))
    sb /= norm
    return sb
