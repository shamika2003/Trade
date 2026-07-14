from core.logger import log
import threading


class CommandControl:


    def __init__(self):

        self.running = True

        self.report_requested = False

        self.paused = False



    def start(self):

        thread = threading.Thread(

            target=self.listen,

            daemon=True

        )

        thread.start()



    def listen(self):


        while self.running:


            try:


                cmd = input(
                    "COMMAND > "
                ).lower().strip()



                if cmd == "stop":


                    self.running = False


                    log(
                        "INFO | Stop command received"
                    )



                elif cmd == "report":


                    self.report_requested = True


                    log(
                        "INFO | Report requested"
                    )



                elif cmd == "status":


                    if self.paused:

                        print(
                            "BOT STATUS : PAUSED"
                        )

                    else:

                        print(
                            "BOT STATUS : RUNNING"
                        )



                elif cmd == "pause":


                    self.paused = True


                    print(
                        "BOT PAUSED"
                    )



                elif cmd == "resume":


                    self.paused = False


                    print(
                        "BOT RESUMED"
                    )



                elif cmd == "exit":


                    self.running = False


                    break



                else:


                    print(
                        "Commands: start stop pause resume report status exit"
                    )


            except:


                break