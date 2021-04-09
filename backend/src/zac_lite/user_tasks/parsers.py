from djangorestframework_camel_case.parser import CamelCaseJSONParser


class NoUnderscoreBeforeNumberCamelCaseJSONParser(CamelCaseJSONParser):
    json_underscoreize = {"no_underscore_before_number": True}
