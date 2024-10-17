
def sum_dict_value(d: dict, limit, pair=None,_type_data=int):
    _sum = 0
    for k, v in d.items():
        if str(k).isdigit() and v and str(v).replace('.','',1).replace(',','',1).isdigit() and k < limit:
            if str(k).isdigit() and pair == True and (k+1)%2 == 0:
                _sum += _type_data(float(v))
            elif str(k).isdigit() and pair == False and (k+1)%2 != 0:
                _sum += _type_data(float(v))
            elif pair == None:
                _sum += _type_data(float(v))
        elif not str(k).isdigit() and v and str(v).replace('.','',1).replace(',','',1).isdigit():
            _sum += _type_data(float(v))
    return _sum
