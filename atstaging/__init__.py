
def component_order(dash=False, suffix=''):

    order = [
        'PACParietal',
        'PACFrontal',
        'PACSensorimotor',
        'PACOccipital',
        'PTCMedialTemporal',
        'PTCRightParietalTemporal',
        'PTCLeftParietalTemporal',
        'PTCOccipital',
        'PTCFrontal',
        'PTCSensorimotor',
        'PTCInsularMedialFrontal'
        ]
    
    if dash:
        order = [x.replace('PAC', 'PAC-').replace('PTC','PTC-') for x in order]
    
    order = [x + suffix for x in order]

    return order