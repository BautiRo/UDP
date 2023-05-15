import time

# Estimacion del Timeout
estimatedRTT = 0.01
devRTT = 0.001
startTime = 0.0

def start():
    global startTime
    startTime = time.perf_counter()

def getUpdatedTimeout():
    global estimatedRTT
    global devRTT
    sampleRTT = time.perf_counter() - startTime
    estimatedRTT = 0.875*estimatedRTT + 0.125*sampleRTT
    devRTT = 0.75*devRTT + 0.25*abs(sampleRTT - estimatedRTT)
    timeoutInSec = estimatedRTT + 4*devRTT
    
    return timeoutInSec
