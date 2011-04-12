# See http://geography.uoregon.edu/datagraphics/color_scales.htm 

def dec_to_255(colors):
    return [tuple(c*255.0 for c in color) for color in colors]

paired_colors = [
   (1.000, 0.750, 0.500),
   (1.000, 0.500, 0.000),
   (1.000, 1.000, 0.600),
   (1.000, 1.000, 0.200),
   (0.700, 1.000, 0.550),
   (0.200, 1.000, 0.000),
   (0.650, 0.930, 1.000),
   (0.100, 0.700, 1.000),
   (0.800, 0.750, 1.000),
   (0.400, 0.300, 1.000),
   (1.000, 0.600, 0.750),
   (0.900, 0.100, 0.200),
   ]

paired_colors_255 = dec_to_255(paired_colors)