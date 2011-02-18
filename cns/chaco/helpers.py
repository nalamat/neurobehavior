from enthought.chaco.api import PlotGrid

def add_default_grids(plot, 
        major_index=None,
        minor_index=None,
        major_value=None, 
        minor_value=None):

    if major_index is not None:
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_style='solid',
                line_color='lightgray',
                grid_interval=major_index)
        plot.underlays.append(grid)

    if minor_index is not None:
        grid = PlotGrid(mapper=plot.index_mapper, component=plot,
                orientation='vertical', line_style='dot',
                line_color='lightgray',
                grid_interval=minor_index)
        plot.underlays.append(grid)

    if major_value is not None:
        grid = PlotGrid(mapper=plot.value_mapper, component=plot,
                orientation='horizontal', line_style='solid',
                line_color='lightgray',
                grid_interval=major_value)
        plot.underlays.append(grid)

    if minor_value is not None:
        grid = PlotGrid(mapper=plot.value_mapper, component=plot,
                orientation='horizontal', line_style='dot',
                line_color='lightgray',
                grid_interval=minor_value)
        plot.underlays.append(grid)
