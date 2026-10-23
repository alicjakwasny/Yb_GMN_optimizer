import pyvisa, time
import numpy as np


class OsaDevice:
    # Na podstawie kodu Ksawerego
    def __init__(self):
        self.connected = False
        self.repeat_sweeps = False
        self.ip = "10.112.161.147"
        self.port = "10001"

        ans = self.osa_connect()
        print(ans)

    def osa_connect(self):
        if not self.connected:
            self.address = "TCPIP::" + self.ip + "::" + self.port + "::SOCKET"

            self.rm = pyvisa.ResourceManager()
            try:
                self.osa = self.rm.open_resource(self.address)

                self.osa.read_termination = "\r\n"
                self.osa.write_termination = "\r\n"
                #self.osa.timeout = 10000
                self.osa.query("OPEN \"anonymous\"")
                self.osa.query("password")
                self.connected = True
                return "Successfully connected to OSA"

            except:
                return "PyVISA Resource Manager failed to reach the device. Please, double check the IP and port."

        else:
             return "Already connected to OSA"

    def osa_disconnect(self):
        if self.connected:
            self.osa.close()
            self.connected = False
            return "Disconnected form OSA"
        else:
            return "OSA was already disconnected"

    def single(self):
        #self.upload_settings()
        self.repeat_sweeps = False

        #initiate sweep
        self.osa.write(":init:smode SING")
        self.osa.write("*CLS")      # clean status
        self.osa.write(":init")

        # wait till sweep finishes
        while True:
            time.sleep(0.1)
            status = int(self.osa.query(":stat:oper:even?"))
            if status == 1:
                # Single sweep completed
                break

        self.download_data()
        return self.xdata, self.ydata

    def auto(self):
        #self.upload_settings()

        self.osa.write(':init:smode AUTO')
        self.osa.write('*CLS')
        self.osa.write(":init")

        for i in range(200):
            time.sleep(0.1)
            status = int(self.osa.query(":stat:oper:even?"))
            if status == 16:
                self.repeat_sweeps = True
                self.download_data_non_stop()
                break

        if not self.repeat_sweeps:
            self.stop()

    def stop(self):
        self.repeat_sweeps = False
        self.osa.write(":ABOR")

    def repeat(self):
        #self.upload_settings()
        self.repeat_sweeps = True

        #initiate sweep
        self.osa.write(":init:smode REP")
        self.osa.write("*CLS")
        self.osa.wite(":init")
        self.download_data_non_stop()

    def download_data_non_stop(self):
        self.download_data()
        if self.repeat_sweeps:
            self.root.after(500, self.download_data_non_stop())

    def download_data(self):
        self.xdata = self.osa.query(":trac:data:X? TRA")
        self.ydata = self.osa.query(":trac:data:Y? TRA")

        def csv_string_to_array(csv_str):
            # Split the string by commas, strip whitespaces and convert to floats
            values = [float(val.strip()) for val in csv_str.strip().split(',')]
            return np.array(values)

        self.xdata = csv_string_to_array(self.xdata)*1e9
        self.ydata = csv_string_to_array(self.ydata)

        self.osa.write(":disp:trac:Y1:rlev " + str(1.05*np.max(self.ydata)/1000))

        return self.xdata, self.ydata

    def upload_settings(self, lambda_center, span, speed, resolution):
        self.osa.write(f":sens:wav:cent {lambda_center} nm")
        self.osa.write(f":sems:wav:span {span} nm")
        self.osa.write(f":sens:sens {speed}")
        self.osa.write(f":disp:trac:Y1:spac LOG")
        self.osa.write(f":sens:band:res {resolution} nm")

if __name__ == "__main__":
    dev = OsaDevice()
    xdata, ydata = dev.download_data()
    print(xdata[:5])
    print(ydata[:5])
    dev.osa_disconnect()


