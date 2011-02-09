
class AveragedChannelView(ChannelView):

    channel = Instance(SnippetChannel)
    index = Instance(ArrayDataSource)
    average_signal = Instance(ArrayDataSource)

    plots = List(LinePlot)
    average_plot = Instance(LinePlot)

    index_mapper = Instance(LinearMapper)
    value_mapper = Instance(LinearMapper)

    def _index_mapper_default(self):
        return LinearMapper(range=self.index_range)

    def _value_mapper_default(self):
        return LinearMapper(range=self.value_range)

    def _container_default(self):
        container = OverlayPlotContainer(
                fill_padding=True,
                padding=40,
                )

        ax = PlotAxis(orientation='bottom',
                mapper=self.index_mapper,
                component=container)
        container.overlays.append(ax)
        ax = PlotAxis(orientation='left',
                mapper=self.value_mapper,
                component=container)
        container.overlays.append(ax)

        return container

    def _channel_changed(self, channel):
        self.container.remove(*self.plots)
        self.index = ArrayDataSource(channel.t)

        for s in channel.signal:
            plot = LinePlot(index=self.index,
                            value=ArrayDataSource(s),
                            index_mapper=self.index_mapper,
                            value_mapper=self.value_mapper,
                            color='gray',
                            alpha=0.5,
                            )
            self.plots.append(plot)
            self.container.add(plot)

        if channel.buffered:
            self.average_signal = ArrayDataSource(channel.average_signal)
        else:
            # Right now the Chaco library does not deal well with NaN values.
            # Such values occur when there is no buffered data (i.e.
            # average_signal returns an array of NaN), so we check to see if any
            # data has been buffered.  If not, we simply set the average signal
            # to zero.
            self.average_signal = ArrayDataSource(np.zeros(channel.samples))

        plot = LinePlot(index=self.index,
                        value=self.average_signal,
                        index_mapper=LinearMapper(range=self.index_range),
                        value_mapper=LinearMapper(range=self.value_range),
                        color='black',
                        line_width=2,
                        )
        self.container.add(plot)
        self.average_plot = plot

    @on_trait_change('channel:updated')
    def update_signal(self, channel, name, info):
        remove, add = info

        if remove:
            self.container.remove(*self.plots[:remove])
            self.plots = self.plots[remove:]

        if add:
            for s in channel.signal[-add:]:
                plot = LinePlot(index=self.index,
                                value=ArrayDataSource(s),
                                index_mapper=LinearMapper(range=self.index_range),
                                value_mapper=LinearMapper(range=self.value_range),
                                color='gray',
                                alpha=0.5,
                                )
                self.plots.append(plot)
                self.container.add(plot)

        if add or remove:
            self.average_signal.set_data(channel.average_signal)
            self.container.raise_component(self.average_plot)

