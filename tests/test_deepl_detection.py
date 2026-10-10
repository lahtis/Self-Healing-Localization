from shl.language_validator import LanguageValidator
v = LanguageValidator()
for x in ["zh-TW", "zh-HK", "zh-CN"]:
    info = v.get_language_info(x)
    print(x, info.get("bcp47"), info.get("default_region"), info.get("default_script"))
