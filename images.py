"""
Image utility functions for memseg and related conversion scritps.
Utilizes numpy extensively. All images are numpy arrays in memory.
"""

from numpy import dtype, iinfo, bool_, int8, uint8, int16, int32, int64, uint16, uint32, uint64, float32, float64

__all__ = [
    'IM_BIT','IM_BYTE','IM_SBYTE','IM_SHORT','IM_SHORT_BE','IM_USHORT','IM_USHORT_BE','IM_INT','IM_INT_BE','IM_UINT','IM_UINT_BE','IM_LONG','IM_LONG_BE','IM_ULONG','IM_ULONG_BE',
    'IM_RGB24','IM_RGB24_STRUCT','IM_FLOAT','IM_DOUBLE',
    'is_rgb24', 'is_image_besides_rgb24', 'is_image',
    'Rectangle','get_foreground_area','fill_background','crop','pad',
    'gauss_blur','flip_up_down','bw','imhist','histeq','label','relabel','consecutively_number','float_image',
    'imread','imsave','imread_mat',
    ]

# The image types we know about
IM_BIT       = dtype(bool_)
IM_BYTE      = dtype(uint8)
IM_SBYTE     = dtype(int8)
IM_SHORT     = dtype(int16).newbyteorder('<')
IM_SHORT_BE  = dtype(int16).newbyteorder('>')
IM_USHORT    = dtype(uint16).newbyteorder('<')
IM_USHORT_BE = dtype(uint16).newbyteorder('>')
IM_INT       = dtype(int32).newbyteorder('<')
IM_INT_BE    = dtype(int32).newbyteorder('>')
IM_UINT      = dtype(uint32).newbyteorder('<')
IM_UINT_BE   = dtype(uint32).newbyteorder('>')
IM_LONG      = dtype(int64).newbyteorder('<')
IM_LONG_BE   = dtype(int64).newbyteorder('>')
IM_ULONG     = dtype(uint64).newbyteorder('<')
IM_ULONG_BE  = dtype(uint64).newbyteorder('>')
IM_RGB24     = dtype((uint8,3))
IM_RGB24_STRUCT = dtype([('R',uint8),('G',uint8),('B',uint8)])
IM_FLOAT     = dtype(float32)
IM_DOUBLE    = dtype(float64)

_signed2unsigned = {IM_SBYTE:IM_BYTE,
                    IM_SHORT:IM_USHORT,IM_SHORT_BE:IM_USHORT_BE,
                    IM_INT  :IM_UINT,  IM_INT_BE  :IM_UINT_BE,
                    IM_LONG :IM_ULONG, IM_LONG_BE :IM_ULONG_BE}
_unsigned_types = (IM_BIT, IM_BYTE, IM_USHORT, IM_UINT, IM_ULONG)

_integer_types = (IM_BIT, 
    IM_BYTE, IM_USHORT, IM_USHORT_BE, IM_UINT, IM_UINT_BE, IM_ULONG, IM_ULONG_BE,
    IM_SBYTE, IM_SHORT, IM_SHORT_BE, IM_INT, IM_INT_BE, IM_LONG, IM_LONG_BE)
_min_max_values = { dt:(iinfo(dt).min,iinfo(dt).max) for dt in _integer_types if dt != IM_BIT }
_min_max_values[IM_BIT] = (False, True)
_min_max_values[IM_FLOAT]  = (float32(0.0),float32(1.0))
_min_max_values[IM_DOUBLE] = (float64(0.0),float64(1.0))

def _get_min_max(im):
    if isinstance(im, dtype): return _min_max_values[im]
    if im.dtype in (IM_FLOAT, IM_DOUBLE):
        mn, mx = im.min(), im.max()
        return (mn, mx) if mn < 0.0 or mx > 1.0 else _min_max_values[im.dtype]
    else:
        return _min_max_values[im.dtype]
def is_rgb24(im): return im.ndim == 2 and im.dtype == IM_RGB24_STRUCT or im.ndim == 3 and im.shape[2] == 3 and im.dtype == IM_BYTE
def is_image_besides_rgb24(im): return im.ndim == 2 and (im.dtype in _integer_types or im.dtype in (IM_FLOAT, IM_DOUBLE))
def is_image(im): return is_rgb24(im) or is_image_besides_rgb24(im)

class Rectangle:
    def __init__(self,t,l,b,r): self.__rect = (t,l,b,r)
    def __repr__(self): return "%d,%d,%d,%d" % self.__rect

    @property
    def rect(self): return self.__rect
    
    @property
    def T(self): return self.__rect[0]
    @property
    def L(self): return self.__rect[1]
    @property
    def B(self): return self.__rect[2]
    @property
    def R(self): return self.__rect[3]
    
    @property
    def Y(self): return self.__rect[0]
    @property
    def X(self): return self.__rect[1]
    @property
    def H(self): return self.__rect[2] - self.__rect[0]
    @property
    def W(self): return self.__rect[3] - self.__rect[1]

def get_foreground_area(im, bg=None):
    """Get the area of the foreground. If bg is not given, it is calculated from the edges of the image."""
    shp = im.shape
    t,l,b,r = 0, 0, shp[0]-1, shp[1]-1
    if bg == None:
        # Calculate bg color using solid strips on top, bottom, left, or right
        if all(im[0,:] == im[0,0]) or all(im[:,0] == im[0,0]):
            bg = im[0,0]
        elif all(im[-1,:] == im[-1,-1]) or all(im[:,-1] == im[-1,-1]):
            bg = im[-1,-1]
        else: return Rectangle(t,l,b,r) # no discoverable bg color, return the entire image
    while t < shp[0]-1 and all(im[t,:] == bg): t += 1
    while b > t        and all(im[b,:] == bg): b -= 1
    while l < shp[1]-1 and all(im[:,l] == bg): l += 1
    while r > l        and all(im[:,r] == bg): r -= 1
    return Rectangle(t,l,b,r)

def fill_background(im, rect=None, bg=0, mirror=False):
    """
    Fills the 'background' of the image with 'bg' or if mirror it True then a reflection of the foreground.
    The foreground is given by the rectangle. If the rectangle is not given, it is calculated with get_foreground_area.
    Currently when using reflection, the foreground must be wider or taller than the background.
    Operates on the array directly and does not copy it.
    """
    if rect == None: rect = get_foreground_area(im)
    if mirror:
        shp = im.shape
        im[:rect.T,:]   = im[2*rect.T-1:rect.T-1:-1,:]
        im[:,:rect.L]   = im[:,2*rect.L-1:rect.L-1:-1]
        im[rect.B+1:,:] = im[rect.B:2*rect.B-shp[0]+1:-1,:]
        im[:,rect.R+1:] = im[:,rect.R:2*rect.R-shp[1]+1:-1]
    else:
        im[:rect.T,:]   = bg
        im[:,:rect.L]   = bg
        im[rect.B+1:,:] = bg
        im[:,rect.R+1:] = bg
    return im

def crop(im, rect=None):
    """Crops an image, keeping the rectangle. If the rectangle is not given, it is calculated with get_foreground_area. Returns a view, not a copy."""
    if rect == None: rect = get_foreground_area(im)
    return im[rect.T:rect.B+1, rect.L:rect.R+1]

def pad(im,t,l,b,r):
    """Pad an image with 0s. The amount of padding is given by top, left, bottom, and right."""
    # TODO: could use "pad" function instead
    from numpy import zeros
    shp = im.shape
    im_out = zeros((shp[0]+b+t,shp[0]+r+l),dtype=im.dtype)
    im_out[t:t+shp[0],l:l+shp[1]] = im
    return im_out

def gauss_blur(im, sigma = 1.0):
    """Blur an image using a Gaussian blur."""
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(im, sigma = sigma)

def bw(im, threshold=1):
    """
    Convert image to black and white. The threshold is used to determine what is made black and white.
    If positive, every value at or above the threshold will be white and below it will be black.
    If negative, every value at or below the magnitude of the threshold will be white.
    If 0, the result will just be black.
    """
    return (im>=threshold) if threshold>0 else (im<-threshold)

"""Flips an image from top-bottom. The returned value is a view, not a copy, so it will values changed in either will be reflected in the other."""
from numpy import flipud as flip_up_down

def imhist(im, nbins=256):
    """
    Calculate the histogram of an image. By default it uses 256 bins (nbins).
    The 'im' argument can be an array, a path (string), or an iterable of these.
    """
    if isinstance(im, str): im = imread(im)
    if hasattr(im, 'dtype'):
        if not is_image_besides_rgb24(im): raise ValueError('Unsupported image type')
        from numpy import histogram
        mn,mx = _get_min_max(im)
        return histogram(im, nbins, range=(mn,mx+1))[0]
    else:
        from numpy import zeros
        h = zeros(nbins, dtype=int32)
        for i in im: h += imhist(i, nbins)
        return h

def histeq(im, nbins=None, hgram=None):
    """
    Equalize the histogram of an image. This is either to a uniform histogram of
    nbins elements (default 64) or to a custom histogram (hgram). Only supports
    integral image data types.
    """
    from numpy import tile, histogram, vstack, spacing, sqrt, empty
    if not is_image_besides_rgb24(im): raise ValueError('Unsupported image type')
    if hgram == None:
        if nbins == None: nbins = 64
        h_dst = tile(float(im.size)/nbins, nbins)
    elif nbins != None: raise ValueError('Cannot use both nbins and hgram in histeq')
    elif hgram.ndim != 1: raise ValueError('hgram must be a vector')
    else:
        nbins = len(hgram)
        h_dst = hgram*(float(im.size)/sum(hgram)) # Make sure the sum of the bins equals the number pixels
    orig_dtype = im.dtype
    if im.dtype in _signed2unsigned:
        im = im.view(dtype=_signed2unsigned[im.dtype])

    mn,mx = _get_min_max(im)
    h_src = histogram(im,256,range=(mn,mx+1))[0]
    h_src_cdf = h_src.cumsum()
    h_dst_cdf = h_dst.cumsum()

    xx = vstack((h_src, h_src))
    xx[0,255],xx[1,0] = 0,0
    tol = tile(xx.min(0)/2.0,(nbins,1))
    err = tile(h_dst_cdf,(256,1)).T - tile(h_src_cdf,(nbins,1)) + tol
    err[err < -im.size*sqrt(spacing(1))] = im.size
    T = (err.argmin(0)*(mx/(nbins-1.0))).round(out=empty(256, dtype=im.dtype))
    if mx == 255: idx = im # Perfect fit, we don't need to scale the indices
    else: idx = (im*(255.0/mx)).round(out=empty(im.shape, dtype=int32)) # Scale the indices
    return T[idx].view(dtype=orig_dtype)

"""
Performs a connected-components analysis on the provided image. 0s are considered background.
Any other values are connected into consecutively numbered contigous regions (where contigous is having a neighbor above, below, left, or right).
Returns the labeled image and the max label value.
"""
try:
    from scipy.ndimage import label
except:
    def label(im): raise ImportError()

def relabel(im):
    """
    Relabels a labeled image. Basically, makes sure that all labels are consecutive and checks that every
    label is one connected region. For labels that specified unconnected regions, one connected region is
    given the label previously had and the other is given a new label that is greater than all other labels.
    Returns the labeled image and the max label value.
    """
    from scipy.ndimage import label
    im,N = consecutively_number(im)
    _,mx = _get_min_max(im)
    for i in range(1, N+1):
        l,n = label(im==i)
        if N+n-1 > mx:
            # The new set of labels is larger than the current data type can store
            im,_ = _conv_type(im, N+n-1)
            _,mx = _get_min_max(im)
        for j in range(2, n+1):
            N = N+1
            im[l==j] = N
    return im, N

def consecutively_number(im):
    """
    Creates a consecutively numbered image from an image.
    0 (or 0,0,0 for RGB) is the only value allowed to become 0 in the resulting image.
    Order is maintained. Note: Currently signed types where negative values are actually used are not supported.
    Returns the re-numbered image and the max number assigned.
    """
    # TODO: support using the same numbers across multiple slices
    from numpy import unique, insert, searchsorted
    # See scipy-lectures.github.io/advanced/image_processing/#measuring-objects-properties-ndimage-measurements for the unqiue/searchsorted method
    if is_rgb24(im):
        # RGB takes special care, and takes a little longer
        im = im.view(dtype=IM_RGB24_STRUCT).squeeze() # converting from IM_RGB24 to IM_RGB24_STRUCT has the 3rd dimension we need to get rid of
        values = unique(im)
        if tuple(values[0]) != (0, 0, 0): values = insert(values, 0, (0, 0, 0)) # make sure only 0 becomes 0 (may need to insert uint8(0) instead)
    elif is_image_besides_rgb24(im):
        # Make sure all the labels are consective starting from 1 and convert to IM_UINT
        values = unique(im)
        if values[0] < 0:
            raise ValueError('negative numbers')
            # TODO: negative values exist, a little harder (the code below 'works' but does not keep 0 in the 0 position...
            #pos0 = searchsorted(values, 0)
            #if pos0 == len(values) or values[pos0] != 0: values = insert(values, pos0, 0) # make sure only 0 becomes 0
        else:
            # only positive, easier
            if values[0] != 0: values = insert(values, 0, 0) # make sure only 0 becomes 0
            if im.dtype != IM_FLOAT and im.dtype != IM_DOUBLE and values[-1] == len(values) - 1: return _conv_type(im, len(values)-1) # have consecutive numbers starting at 0 already, straight numeric conversion
    else: raise ValueError('im')
    return _conv_type(searchsorted(values, im), len(values)-1)

def _conv_type(im, n):
    for dtype in _unsigned_types:
        if n <= _get_min_max(dtype)[1]:
            return im.astype(dtype), n
    raise OverflowError()

def float_image(im, in_scale = None, out_scale = (0.0, 1.0)):
    """
    Convert an image into a 32-bit floating-point image by scaling the data. Does not support RGB images.
    in_scale must be a length-2 list/tuple specifying lower and upper bounds.
    If in_scale is not provided or is None then the bounds of the underlying type is used (e.g. it is (0, 255) for IM_BYTE)
    out_scale is the range of floating-point numbers to map to, defaulting to 0.0 to 1.0
    """
    
    from numpy import empty, multiply, add
    
    # Process arguments
    if im.dtype == IM_RGB24_STRUCT: raise ValueError('im') # cannot float RGB image
    if in_scale == None: in_scale = _get_min_max(im)
    elif len(in_scale) != 2 or in_scale[0] >= in_scale[1]: raise ValueError('in_scale')
    if len(out_scale) != 2 or out_scale[0] >= out_scale[1]: raise ValueError('out_scale')

    # Perform conversion
    in_min = in_scale[0]
    out_min = out_scale[0]
    k = float(out_scale[1] - out_min) / (in_scale[1] - in_min)
    out = empty(im.shape, dtype=IM_FLOAT)
    return add(multiply(im, k, out), out_min - in_min, out)

def imread_mat(filename, name = None):
    """
    Read an 'image' from a MATLAB .MAT file. The file can be any version. Files
    that are v7.3 require the h5py module. If no name is given, the first
    variable is taken.
    """
    try:
        # Try general first (doesn't work for v7.3+ files)
        # SciPy has this built in
        # Supports loading just the given variable name
        # Otherwise have to load all variables and skip special keys starting with "__" to find the variable to load
        # Loaded matracies are already arrays
        from scipy.io import loadmat
        if name == None:
            try:
                # Try to get first variable name without loading entire file (only supported in SciPy 0.12+)
                from scipy.io import whosmat
                keys in whosmat(file_name)
                if len(keys) == 0: raise KeyError()
                name = keys[0][0]
            except: pass
        x = loadmat(filename, variable_names = name)
        if name == None:
            name = '__' # we need to find first
            for name in x.keys():
                if name[:2] != '__': break
            if name[:2] == '__': raise KeyError() # no variables
        return x[name] # can raise key error
    except NotImplementedError:
        # Try v7.3 file which is an HDF5 file
        # We have to use h5py for this (or PyTables...)
        # Always loads entire metadata (not just specific variable) but none of the data
        # Data needs to be actually loaded (.value) and transposed (.T)
        from h5py import File as HDF5File # TODO: if import error try using PyTables
        with HDF5File(filename, 'r') as x: # IOError if it doesn't exist or is the wrong format
            if name == None:
                try: name = next(iter(x.keys()))
                except StopIteration: raise KeyError() # no variables
            return x[name].value.T # can raise key error

def imread(filename):
    """
    Read an image using SciPy (actually PIL) for any formats it supports.

    Additionally, the following extra formats are supported (extension must be right):
        MHA/MHD:    8-bit gray, 16-bit gray, 32-bit gray, 64-bit gray, float, double, 24-bit RGB
        MAT:        all formats, may not be image-like (requires h5py module for newer MAT files)
    Note: both only get the first "image" or data from the file.
    
    PIL Common Supported Formats: (not all-inclusive)
        PNG:  1-bit BW, 8-bit gray, 16-bit gray, 24-bit RGB
        TIFF: 1-bit BW, 8-bit gray, 16-bit gray, 24-bit RGB [not ZIP compressed]
        BMP:  1-bit BW, 8-bit gray, 24-bit RGB
        JPEG: 8-bit gray, 24-bit RGB
        IM:   all?
        
    See http://www.pythonware.com/library/pil/handbook/formats.htm for more details
    MHA/MHD code is implemented in the metafile module. MAT code is implemented in this module.
    """
    from os.path import splitext

    ext = splitext(filename)[1].lower()
    if ext == '.mat':   return imread_mat(filename)
    elif ext == '.mha':
        from .metafile import imread_mha
        return imread_mha(filename)[1]
    elif ext == '.mhd':
        from .metafile import imread_mhd
        return imread_mhd(filename)[1]
    else:
        from scipy.misc import imread
        im = imread(filename)
        if im.dtype == IM_BIT:
            # Bugs in SciPy cause 1-bit images to be read as corrupted
            from PIL import Image
            from numpy import asarray
            im = Image.open(filename)
            im = asarray(im.getdata(), dtype=IM_BIT).reshape(im.size)
        return im

def imsave(filename, im):
    """
    Save an image. It will use SciPy (actually PIL) for any formats it supports.

    Additionally, the following extra formats are supported (extension must be right):
        MHA/MHD:    8-bit gray, 16-bit gray, 32-bit gray, 64-bit gray, float, double, 24-bit RGB
    
    PIL Common Supported Formats: (not all-inclusive)
        PNG:  1-bit BW, 8-bit gray, 16-bit gray, 24-bit RGB
        TIFF: 1-bit BW, 8-bit gray, 16-bit gray, 24-bit RGB
        BMP:  1-bit BW, 8-bit gray, 24-bit RGB
        JPEG: 8-bit gray, 24-bit RGB
        IM:   all?
    
    See thtp://www.pythonware.com/library/pil/handbook/formats.htm for more details
    MHA/MHD code is implemented in the metafile module.
    """
    from os.path import splitext
    
    ext = splitext(filename)[1].lower()
    if ext == '.mha':
        from .metafile import imsave_mha
        imsave_mha(filename, im)
    elif ext == '.mhd':
        from .metafile import imsave_mhd
        imsave_mhd(filename, im)
    elif im.dtype == IM_BIT:
        # Make sure data is actually saved as 1-bit data
        from PIL import Image
        im = im * uint8(255)
        Image.frombuffer('L', im.shape, im.data, 'raw', 'L', 0, 1).convert('1').save(filename)
    else:
        from scipy.misc import imsave
        imsave(filename, im)
