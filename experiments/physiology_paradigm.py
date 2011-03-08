from abstract_experiment_paradigm import AbstractExperimentParadigm

class PhysiologyParadigm(AbstractExperimentParadigm):

    # We can monitor up to four channels.  These map to DAC outputs 9, 10, 11
    # and 12 on the RZ5.  The first output (9) also goes to the speaker.
    monitor_settings    = List(Instance(MonitorSetting))

    # We adjust two key settings, whether the channel is visible in the plot and
    # the differentials to apply to it.
    channel_settings    = List(Instance(ChannelSetting))

    plot_mode           = Enum('continuous', 'triggered')

    def _index_range_default(self):
        return ChannelDataRange(range=10, interval=8)

    def _monitor_settings_default(self):
        return [MonitorSetting(number=i) for i in range(1, 5)]

    def _channel_settings_default(self):
        return [ChannelSetting(number=i) for i in range(1, 17)]

    # List of the channels visible in the plot
    visible_channels = Property(depends_on='channel_settings.visible')

    @cached_property
    def _get_visible_channels(self):
        return [i for i, ch in enumerate(self.channel_settings) if ch.visible]

    # Generates the matrix that will be used to compute the differential for the
    # channels.  This matrix will be uploaded to the RZ5.
    diff_matrix = Property(depends_on='channel_settings.differential')

    @cached_property
    def _get_diff_matrix(self):
        n_chan = len(self.channel_settings)
        map = np.zeros((n_chan, n_chan))
        for channel in self.channel_settings:
            channels = to_list(channel.differential)
            if len(channels) != 0:
                sf = -1.0/len(channels)
                for d in channels:
                    map[channel.number, d-1] = sf
        return map

    # When the visible channels change, we need to update the plot!
    @on_trait_change('visible_channels')
    def _update_plot(self):
        self.raw_plot.visible = self.visible_channels

    # If plot offset or number of visible channels change, we need to update the
    # value range accordingly.
    @on_trait_change('visible_channels, plot_offset')
    def _update_range(self):
        offset = self.raw_plot.offset
        self.range.high_setting = offset*len(self.visible_channels)

    # Filter cutoff
    fc_low      = Float(10e3)
    fc_high     = Float(300)

