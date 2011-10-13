from enthought.traits.api import HasTraits, Instance, List, on_trait_change
from enthought.chaco.api import OverlayPlotContainer, LinePlot, ScatterPlot, \
        add_default_grids, add_default_axes, DataRange1D, LinearMapper, \
        LogMapper, ArrayDataSource
from enthought.chaco.tools.api import PanTool, ZoomTool
from enthought.traits.ui.api import View, Item, HGroup, VGroup
from enthought.enable.api import ComponentEditor

class CalibrationPlot(HasTraits):

    calibrations = List(Instance('neurogen.calibration.Calibration'))
    magnitude_plot = Instance('enable.component.Component')
    phase_plot = Instance('enable.component.Component')
    impulse_plot = Instance('enable.component.Component')

    def _get_cal_data(self, calibration):
        ref_freq = calibration.ref_frequencies
        ref_spl = calibration.get_max_spl(ref_freq)
        ref_phase = calibration.get_phase(ref_freq)
        fir = calibration.fir_coefficients
        import numpy as np
        t_fir = np.arange(len(fir))*100e-3*1e3
        ref_freq = ArrayDataSource(ref_freq)
        ref_spl = ArrayDataSource(ref_spl)
        ref_phase = ArrayDataSource(ref_phase)
        fir = ArrayDataSource(fir)
        t_fir = ArrayDataSource(t_fir)
        return ref_freq, ref_spl, ref_phase, t_fir, fir

    @on_trait_change('calibrations')
    def _create_plots(self):
        padding = [50, 10, 10, 50]
        magnitude_plot = OverlayPlotContainer(padding=padding)
        phase_plot = OverlayPlotContainer(padding=padding)
        impulse_plot = OverlayPlotContainer(padding=padding)

        freq_range = DataRange1D()
        freq_mapper = LogMapper(range=freq_range)
        spl_range = DataRange1D()
        spl_mapper = LinearMapper(range=spl_range)
        phase_range = DataRange1D()
        phase_mapper = LinearMapper(range=phase_range)

        # Impulse plot range/mappers
        fir_range = DataRange1D()
        fir_mapper = LinearMapper(range=fir_range)
        t_fir_range = DataRange1D()
        t_fir_mapper = LinearMapper(range=t_fir_range)

        colors = ('blue', 'orange')
        for i, (cal, color) in enumerate(zip(self.calibrations, colors)):
            freq, spl, phase, t_fir, fir = self._get_cal_data(cal)
            freq_range.add(freq)
            spl_range.add(spl)
            phase_range.add(phase)
            fir_range.add(fir)
            t_fir_range.add(t_fir)

            m_plot = LinePlot(index=freq, value=spl, index_mapper=freq_mapper,
                    value_mapper=spl_mapper, color=color, line_width=2)
            p_plot = LinePlot(index=freq, value=phase, index_mapper=freq_mapper,
                    value_mapper=phase_mapper, color=color, line_width=2)
            i_plot = LinePlot(index=t_fir, value=fir, index_mapper=t_fir_mapper,
                    value_mapper=fir_mapper, color=color, line_width=2)

            if i == 0:
                add_default_axes(m_plot, htitle='Frequency (Hz)', 
                        vtitle='dB SPL for 1 Vrms and 0 dB gain')
                add_default_axes(p_plot, vtitle='Phase (radians)',
                        htitle='Frequency (Hz)')
                add_default_axes(i_plot, vtitle='Amplitude (V)',
                        htitle='Time (msec)')
                add_default_grids(m_plot)
                add_default_grids(p_plot)
                add_default_grids(i_plot)
                m_plot.tools.append(PanTool(m_plot, constrain_direction='x',
                    restrict_to_data=False, constrain=True))
                m_plot.overlays.append(ZoomTool(m_plot, tool_mode='range',
                    axis='index'))
                i_plot.overlays.append(ZoomTool(i_plot))

            magnitude_plot.add(m_plot)
            phase_plot.add(p_plot)
            impulse_plot.add(i_plot)

            m_plot = ScatterPlot(index=freq, value=spl, index_mapper=freq_mapper,
                    value_mapper=spl_mapper, color=color, outline_color='white',
                    marker='circle', marker_size=3)
            p_plot = ScatterPlot(index=freq, value=phase, index_mapper=freq_mapper,
                    value_mapper=phase_mapper, color=color, outline_color='white',
                    marker='circle', marker_size=3)

            magnitude_plot.add(m_plot)
            phase_plot.add(p_plot)

        self.magnitude_plot = magnitude_plot
        self.phase_plot = phase_plot
        self.impulse_plot = impulse_plot

    traits_view = View(
            HGroup(
                VGroup(
                    Item('magnitude_plot', show_label=False,
                        editor=ComponentEditor(), height=300, width=600),
                    Item('phase_plot', show_label=False,
                        editor=ComponentEditor(), height=300, width=600),
                    ),
                Item('impulse_plot', show_label=False,
                    editor=ComponentEditor(), height=600, width=600),
                ),
            resizable=True,
            )

if __name__ == '__main__':
    from cns import get_config
    from neurogen.calibration import load_mat_cal
    c1 = load_mat_cal(get_config('CAL_PRIMARY'))
    c2 = load_mat_cal(get_config('CAL_SECONDARY'))
    CalibrationPlot(calibrations=[c1, c2]).configure_traits()
