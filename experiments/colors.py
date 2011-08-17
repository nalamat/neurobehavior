# See http://geography.uoregon.edu/datagraphics/color_scales.htm 

color_names = {
    'light green': '#98FB98',
    'dark green': '#2E8B57',
    'light red': '#FFC8CB',
    'dark red': '#FA8072',
    'gray': '#D3D3D3',
    'light blue': '#ADD8E6',
    'white': '#FFFFFF',
          }


def dec_to_255(colors):
    return [tuple(c*255.0 for c in color) for color in colors]

paired_colors = [
   (0.900, 0.100, 0.200),
   (1.000, 0.600, 0.750),
   (0.400, 0.300, 1.000),
   (0.800, 0.750, 1.000),
   (0.100, 0.700, 1.000),
   (0.650, 0.930, 1.000),
   (0.200, 1.000, 0.000),
   (0.700, 1.000, 0.550),
   (1.000, 1.000, 0.200),
   (1.000, 1.000, 0.600),
   (1.000, 0.500, 0.000),
   (1.000, 0.750, 0.500),
   ]

paired_colors_255 = dec_to_255(paired_colors)
