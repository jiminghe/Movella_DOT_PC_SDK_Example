
#  Copyright (c) 2003-2023 Movella Technologies B.V. or subsidiaries worldwide.
#  All rights reserved.
#  
#  Redistribution and use in source and binary forms, with or without modification,
#  are permitted provided that the following conditions are met:
#  
#  1.	Redistributions of source code must retain the above copyright notice,
#  	this list of conditions and the following disclaimer.
#  
#  2.	Redistributions in binary form must reproduce the above copyright notice,
#  	this list of conditions and the following disclaimer in the documentation
#  	and/or other materials provided with the distribution.
#  
#  3.	Neither the names of the copyright holders nor the names of their contributors
#  	may be used to endorse or promote products derived from this software without
#  	specific prior written permission.
#  
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
#  EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
#  THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
#  OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
#  HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY OR
#  TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#  

# Requires installation of the correct Movella DOT PC SDK wheel through pip
# For example, for Python 3.9 on Windows 64 bit run the following command
# pip install movelladot_pc_sdk-202x.x.x-cp39-none-win_amd64.whl


##Payload Reference Information(WARNING: high bytes would cause data loss, use less data rate or less bytes payload to avoid data loss)
#Custom mode 1: Timestamp, Euler, Free acceleration, Angular velocity
#Custom mode 2: 34 bytes, Timestamp, Euler, Free acceleration, Magnetic field
#Custom mode 3: 32 bytes, Timestamp, Quaternion, Angular velocity
#Custom mode 4: 51 bytes, timestamp, inertial data in high fidelity mode, quaternion, magnetic field data and status
#Custom mode 5: 44 bytes, Timestamp, Quaternions, Acceleration, Angular velocity

from xdpchandler import *
import datetime
import os

if __name__ == "__main__":
    xdpcHandler = XdpcHandler()

    if not xdpcHandler.initialize():
        xdpcHandler.cleanup()
        exit(-1)

    xdpcHandler.scanForDots()
    if len(xdpcHandler.detectedDots()) == 0:
        print("No Movella DOT device(s) found. Aborting.")
        xdpcHandler.cleanup()
        exit(-1)

    xdpcHandler.connectDots()

    if len(xdpcHandler.connectedDots()) == 0:
        print("Could not connect to any Movella DOT device(s). Aborting.")
        xdpcHandler.cleanup()
        exit(-1)

    for device in xdpcHandler.connectedDots():
        filterProfiles = device.getAvailableFilterProfiles()
        print("Available filter profiles:")
        for f in filterProfiles:
            print(f.label())

        print(f"Current profile: {device.onboardFilterProfile().label()}")
        if device.setOnboardFilterProfile("General"):
            print("Successfully set profile to General")
        else:
            print("Setting filter profile failed!")
            
        print(f"Current data rate: {device.outputRate()} Hz.")
        outputRate_Toset = 60
        if device.setOutputRate(outputRate_Toset):
            print(f"Successfully set output rate to {outputRate_Toset} Hz.")
        else:
            print("Setting output rate failed!")

        print("Setting quaternion and euler angles CSV output")
        device.setLogOptions(movelladot_pc_sdk.XsLogOptions_QuaternionAndEuler)

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bluetooth_address_str = device.bluetoothAddress().replace(':', '-')
        logFileName = f"logfile_{timestamp_str}_{bluetooth_address_str}.csv"
        # Check if the 'log_files' subfolder exists, and create it if it doesn't
        log_folder_path = 'log_files'
        if not os.path.exists(log_folder_path):
            os.makedirs(log_folder_path)
        
        full_log_file_path = os.path.join(log_folder_path, logFileName)

        print(f"Enable logging to: {full_log_file_path}")

        if not device.enableLogging(full_log_file_path):
            print(f"Failed to enable logging. Reason: {device.lastResultText()}")

        print("Putting device into measurement mode.")
        if not device.startMeasurement(movelladot_pc_sdk.XsPayloadMode_CustomMode5):
            print(f"Could not put device into measurement mode. Reason: {device.lastResultText()}")
            continue

    print("\nMain loop. Recording data for 20 seconds.")
    print("-----------------------------------------")

    # First printing some headers so we see which data belongs to which device
    s = ""
    for device in xdpcHandler.connectedDots():
        s += f"{device.bluetoothAddress():42}"
    print("%s" % s, flush=True)

    orientationResetDone = False
    startTime = movelladot_pc_sdk.XsTimeStamp_nowMs()
    while movelladot_pc_sdk.XsTimeStamp_nowMs() - startTime <= 20000:
        if xdpcHandler.packetsAvailable():
            s = ""
            for device in xdpcHandler.connectedDots():
                s += "Device: " + device.bluetoothAddress() + ", "
                # Retrieve a packet
                packet = xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())
                
                if packet.containsSampleTimeFine():
                    sampleTimeFine = packet.sampleTimeFine()
                    s += "SampleTimeFine: %.0f" % sampleTimeFine

                if packet.containsOrientation():
                    quaternion = packet.orientationQuaternion()
                    s += " |q0: %.2f" % quaternion[0] + ", q1: %.2f" % quaternion[1] + ", q2: %.2f" % quaternion[2] + ", q3: %.2f " % quaternion[3]

                    euler = packet.orientationEuler()
                    s += " |Roll: %.2f" % euler.x() + ", Pitch: %.2f" % euler.y() + ", Yaw: %.2f " % euler.z()
                
                if packet.containsCalibratedAcceleration():
                    acc = packet.calibratedAcceleration()
                    s += " |Acc X: %.2f" % acc[0] + ", Acc Y: %.2f" % acc[1] + ", Acc Z: %.2f" % acc[2]
                
                if packet.containsCalibratedGyroscopeData():
                    gyr = packet.calibratedGyroscopeData() # deg/sec, note for the old sdk, it was radians/sec
                    s += " |Gyr X: %.2f" % gyr[0] + ", Gyr Y: %.2f" % gyr[1] + ", Gyr Z: %.2f" % gyr[2]
                
                if packet.containsFreeAcceleration():
                    freeAcc = packet.freeAcceleration() 
                    s += " |freeAcc X: %.2f" % freeAcc[0] + ", freeAcc Y: %.2f" % freeAcc[1] + ", freeAcc Z: %.2f" % freeAcc[2]
                
                if packet.containsCalibratedMagneticField():
                    mag = packet.calibratedMagneticField() 
                    s += " |mag X: %.2f" % mag[0] + ", mag Y: %.2f" % mag[1] + ", mag Z: %.2f" % mag[2]

                print("%s\r" % s, end="", flush=True)

            if not orientationResetDone and movelladot_pc_sdk.XsTimeStamp_nowMs() - startTime > 5000:
                for device in xdpcHandler.connectedDots():
                    print(f"\nResetting heading for device {device.portInfo().bluetoothAddress()}: ", end="", flush=True)
                    if device.resetOrientation(movelladot_pc_sdk.XRM_Heading):
                        print("OK", end="", flush=True)
                    else:
                        print(f"NOK: {device.lastResultText()}", end="", flush=True)
                print("\n", end="", flush=True)
                orientationResetDone = True
    print("\n-----------------------------------------", end="", flush=True)

    for device in xdpcHandler.connectedDots():
        print(f"\nResetting heading to default for device {device.portInfo().bluetoothAddress()}: ", end="", flush=True)
        if device.resetOrientation(movelladot_pc_sdk.XRM_DefaultAlignment):
            print("OK", end="", flush=True)
        else:
            print(f"NOK: {device.lastResultText()}", end="", flush=True)
    print("\n", end="", flush=True)

    print("\nStopping measurement...")
    for device in xdpcHandler.connectedDots():
        if not device.stopMeasurement():
            print("Failed to stop measurement.")
        if not device.disableLogging():
            print("Failed to disable logging.")

    xdpcHandler.cleanup()
