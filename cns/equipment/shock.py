class ShockSettings(HasTraits):

    max_shock   = CFloat
    shock_curve = Array(dtype='f')
