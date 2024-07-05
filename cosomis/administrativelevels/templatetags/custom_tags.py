from django import template
from django.utils.translation import gettext_lazy
import json
from cosomis.constants import SUB_PROJECT_STATUS_COLOR
from administrativelevels.models import Task
from cosomis.utils import structure_the_words as utils_structure_the_words

register = template.Library()


@register.filter(name="imgAWSS3Filter")
def img_aws_s3_filter(uri):
    return uri.split("?")[0]


@register.filter(name="is_pdf")
def is_pdf(uri):
    uri = uri.split("?")[0]
    return uri.split(".")[-1] in ['pdf', 'docx']


@register.filter(name="not_local")
def not_local(uri):
    return uri.split(":")[0] != 'file'


@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


@register.filter(name='get_group_high')
def get_group_high(user):
    """
    All Groups permissions
        - SuperAdmin            :
        - CDD Specialist        : CDDSpecialist
        - Admin                 : Admin
        - Evaluator             : Evaluator
        - Accountant            : Accountant
        - Regional Coordinator  : RegionalCoordinator
        - National Coordinator  : NationalCoordinator
        - General Manager       : GeneralManager
        - Director              : Director
        - Advisor               : Advisor
        - Minister              : Minister
        - Infra                 : Infra
    """
    if user.is_superuser:
        return gettext_lazy("Principal Administrator").__str__()

    if user.groups.filter(name="Admin").exists():
        return gettext_lazy("Administrator").__str__()
    if user.groups.filter(name="CDDSpecialist").exists():
        return gettext_lazy("CDD Specialist").__str__()
    if user.groups.filter(name="Evaluator").exists():
        return gettext_lazy("Evaluator").__str__()
    if user.groups.filter(name="Accountant").exists():
        return gettext_lazy("Accountant").__str__()
    if user.groups.filter(name="RegionalCoordinator").exists():
        return gettext_lazy("Regional Coordinator").__str__()
    if user.groups.filter(name="NationalCoordinator").exists():
        return gettext_lazy("National Coordinator").__str__()
    if user.groups.filter(name="GeneralManager").exists():
        return gettext_lazy("General Manager").__str__()
    if user.groups.filter(name="Director").exists():
        return gettext_lazy("Director").__str__()
    if user.groups.filter(name="Advisor").exists():
        return gettext_lazy("Advisor").__str__()
    if user.groups.filter(name="Minister").exists():
        return gettext_lazy("Minister").__str__()
    if user.groups.filter(name="Infra").exists():
        return gettext_lazy("Infra").__str__()

    return gettext_lazy("User").__str__()


class MakeListNode(template.Node):
    def __init__(self, items, varname):
        self.items = items
        self.varname = varname

    def render(self, context):
        context[self.varname] = []
        for i in self.items:
            if i.isdigit():
                context[self.varname].append(int(i))
            else:
                context[self.varname].append(str(i).replace('"', ''))
        return ""


@register.tag
def make_list(parser, token):
    bits = list(token.split_contents())
    if len(bits) >= 4 and bits[-2] == "as":
        varname = bits[-1]
        items = bits[1:-2]
        return MakeListNode(items, varname)
    else:
        raise template.TemplateSyntaxError("%r expected format is 'item [item ...] as varname'" % bits[0])


@register.filter(name='get_to_percent_str')
def get_to_percent_str(number):
    """
    converti une valeur de pourcentage en chaine de caractere

    """
    return str(number if number >= 10 else "0" + str(number)) + " %"


@register.filter
def get(dictionary, key):
    return dictionary.get(key, None)


@register.filter
def get_on_list(data, index):
    try:
        return data[index]
    except:
        return None


@register.filter
def isnumber(value):
    return str(value).replace('-', '').replace('.', '', 1).replace(',', '', 1).isdigit()



@register.filter
def join_with_commas(obj_list):
    """Takes a list of objects and returns their string representations,
    separated by commas and with 'and' between the penultimate and final items
    For example, for a list of fruit objects:
    [<Fruit: apples>, <Fruit: oranges>, <Fruit: pears>] -> 'apples, oranges and pears'
    """
    if not obj_list:
        return ""
    l = len(obj_list)
    if l == 1:
        return u"%s" % obj_list[0]
    else:
        return ", ".join(str(obj) for obj in obj_list[:l - 1]) \
            + " " + gettext_lazy("and").__str__() + " " + str(obj_list[l - 1])


@register.filter
def separate_with_space(value, unit=None, show_float=False):
    if unit:
        unit = " " + unit
    else:
        unit = ""

    if not show_float:
        value = round(float(value))

    if not value or not str(value).replace('-', '').replace('.', '', 1).replace(',', '', 1).isdigit():
        return ""

    float_values = str(value).split(',')
    if len(float_values) > 1:
        float_value = float_values[-1]
    else:
        float_value = float_values[0]
    float_values = str(float_value).split('.')
    if len(float_values) > 1:
        float_value = float_values[-1]
    else:
        float_value = None

    value = str(value).split(',')[0].split('.')[0]
    l = len(str(int(value)))
    if l in (0, 1) and int(value) < 1:
        return str(int(value)) + unit

    list_value_str = list(value)
    list_value_str.reverse()
    money_format = ""
    for i in range(1, len(list_value_str) + 1):
        money_format += list_value_str[i - 1]
        if i % 3 == 0:
            money_format += " "

    list_money_format = list(money_format)
    list_money_format.reverse()

    return "".join(list_money_format) + "." + float_value + unit if float_value else "".join(list_money_format) + unit


@register.filter
def remove_zeros_on_zeros(value):
    if not value or not str(value).replace('.', '', 1).replace(',', '', 1).isdigit():
        return ""
    value = str(value).split(',')[0].split('.')[0]
    l = len(str(int(value)))

    if l in (0, 1) and int(value) < 1:
        return int(value)

    return value


@register.filter
def subtract(value, arg):
    return value - arg


@register.filter(name="checkType")
def check_type(elt, _type):
    return type(elt).__name__ == _type


@register.filter
def split(value, key):
    return value.split(key)


@register.simple_tag
def call_method(obj, method_name, *args):
    method = getattr(obj, method_name)
    return method(*args)


@register.filter
def get_step_color(key):
    return SUB_PROJECT_STATUS_COLOR.get(key, '#000000')


@register.filter
def get_item(dictionary, key):
    try:
        return int(dictionary.get(key))
    except ValueError:
        return dictionary.get(key)


@register.filter(name="structureTheFields")
def structure_the_fields(task):
    fields_values = {}
    if task.get("form_response"):
        for fields in task.get("form_response"):
            for field, value in fields.items():
                if type(value) in (dict, list):
                    if type(value) == list:
                        for l_field in value:
                            for field1, value1 in l_field.items():
                                if type(value1) in (dict, list):
                                    if type(value1) == list:
                                        for l_field in value1:
                                            for field2, value2 in l_field.items():
                                                fields_values[field2] = value2
                                    else:
                                        for field3, value3 in value1.items():
                                            if type(value3) == list:
                                                for l_field in value3:
                                                    for field4, value4 in l_field.items():
                                                        fields_values[field4] = value4
                                            else:
                                                fields_values[field3] = value3
                                else:
                                    fields_values[field1] = value1

                    else:
                        for field5, value5 in value.items():
                            if type(value5) in (dict, list):
                                if type(value5) == list:
                                    for l_field in value5:
                                        for field6, value6 in l_field.items():
                                            fields_values[field6] = value6
                                else:
                                    for field7, value7 in value5.items():
                                        fields_values[field7] = value7
                            else:
                                fields_values[field5] = value5
                else:
                    fields_values[field] = value

    return fields_values


@register.filter(name="structureTheFieldsLabels")
def structure_the_fields_labels(task):
    fields_values = []
    if task.get("form_response"):
        i = 0
        form = task.get("form")
        if form is not None:
            for fields in task.get("form_response"):
                fields_options = form[i].get('options').get('fields')
                dict_values = {}
                for field, value in fields.items():
                    label = fields_options.get(field).get('label')
                    if type(value) in (dict, list):
                        if type(value) == list:
                            _list1 = []
                            for l_field in value:
                                item1 = {}
                                for field1, value1 in l_field.items():
                                    if type(value1) in (dict, list):
                                        if type(value1) == list:
                                            _list2 = []
                                            for l_field in value1:
                                                item2 = {}
                                                for field2, value2 in l_field.items():
                                                    item2[field2] = {'name': utils_structure_the_words(field2),
                                                                     'value': value2}
                                                _list2.append(item2)
                                            item1[field1] = {'name': utils_structure_the_words(field1), 'value': _list2}
                                        else:
                                            dict1 = {}
                                            for field3, value3 in value1.items():
                                                if type(value3) == list:
                                                    _list3 = []
                                                    for l_field in value3:
                                                        item4 = {}
                                                        for field4, value4 in l_field.items():
                                                            item4[field4] = {'name': utils_structure_the_words(field4),
                                                                             'value': value4}
                                                        _list3.append(item4)
                                                    dict1[field3] = {'name': utils_structure_the_words(field3),
                                                                     'value': _list3}
                                                else:
                                                    dict1[field3] = {'name': utils_structure_the_words(field3),
                                                                     'value': value3}
                                            item1[field1] = {'name': utils_structure_the_words(field1), 'value': dict1}
                                    else:
                                        item1[field1] = {'name': utils_structure_the_words(field1), 'value': value1}
                                _list1.append(item1)
                            dict_values[field] = {'name': label if label else utils_structure_the_words(field),
                                                  'value': _list1}
                        else:
                            dict2 = {}
                            ii = 0
                            for field5, value5 in value.items():
                                fields1 = fields_options.get(field).get('fields')
                                try:
                                    label1 = fields1[field5].get('label') if fields1[field5].get(
                                        'label') else utils_structure_the_words(field5)
                                except Exception as ex:
                                    label1 = utils_structure_the_words(field5)
                                if type(value5) in (dict, list):
                                    if type(value5) == list:
                                        _list4 = []
                                        for l_field in value5:
                                            item5 = {}
                                            for field6, value6 in l_field.items():
                                                item5[field6] = {'name': utils_structure_the_words(field6), 'value': value6}
                                            _list4.append(item5)
                                        dict2[field5] = {'name': label1, 'value': _list4}
                                    else:
                                        item6 = {}
                                        for field7, value7 in value5.items():
                                            try:
                                                label2 = fields1[field5].get('fields').get(field7).get('label') if fields1[
                                                    field5].get('fields').get(field7).get(
                                                    'label') else utils_structure_the_words(field7)
                                            except Exception as ex:
                                                label2 = utils_structure_the_words(field7)

                                            if type(value7) in (dict, list):
                                                if type(value7) == list:
                                                    _list5 = []
                                                    for l_field in value7:
                                                        item7 = {}
                                                        for field8, value8 in l_field.items():
                                                            item7[field8] = {'name': utils_structure_the_words(field8),
                                                                             'value': value8}
                                                        _list5.append(item7)
                                                    dict2[field5] = {'name': label2, 'value': _list5}
                                                else:
                                                    item8 = {}
                                                    for field9, value9 in value7.items():
                                                        try:
                                                            label3 = fields1[field5].get('fields').get(field7).get(
                                                                'fields').get(field9).get('label') if fields1[field5].get(
                                                                'fields').get(field7).get('fields').get(field9).get(
                                                                'label') else utils_structure_the_words(field9)
                                                        except Exception as ex:
                                                            label3 = utils_structure_the_words(field9)
                                                        item6[field7] = {'name': label3, 'value': value9}
                                                    dict2[field5] = {'name': label2, 'value': item6}
                                            else:
                                                dict2[field7] = {'name': label2, 'value': value7}

                                            # item6[field7] = {'name': label2, 'value': value7}
                                        dict2[field5] = {'name': label1, 'value': item6}
                                else:
                                    dict2[field5] = {'name': label1, 'value': value5}
                                ii += 1
                            dict_values[field] = {'name': label if label else utils_structure_the_words(field),
                                                  'value': dict2}
                    else:
                        dict_values[field] = {'name': label if label else utils_structure_the_words(field), 'value': value}
                fields_values.append(dict_values)
                i += 1
    return fields_values


@register.filter(name="structureTheWords")
def structure_the_words(word):
    return utils_structure_the_words(word)