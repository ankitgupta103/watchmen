try:
    import machine
    print("machine imported")
except Exception as e:
    print("count not import machine")

try:
    rtc = machine.RTC()
except Exception as e:
    print("error in rtc=.., e=", {e})
print("datetime =", rtc.datetime())