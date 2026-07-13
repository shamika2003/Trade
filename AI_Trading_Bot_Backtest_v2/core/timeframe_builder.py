# filename: timeframe_builder.py

import pandas as pd

from core.logger import log



# =====================================================
# CREATE H1 FROM M5
# =====================================================

def create_h1_from_m5(df):

    """
    Converts M5 candles into H1 candles.

    IMPORTANT:
    Completed H1 candle only.
    Prevents future leakage.
    """

    try:


        data = df.copy()



        data["time"] = pd.to_datetime(
            data["time"]
        )


        data = (

            data

            .sort_values(
                "time"
            )

            .set_index(
                "time"
            )

        )



        h1 = (

            data

            .resample(

                "1h",

                label="right",

                closed="right"

            )

            .agg(

                {

                    "open":
                    "first",


                    "high":
                    "max",


                    "low":
                    "min",


                    "close":
                    "last",


                    "tick_volume":
                    "sum",


                    "spread":
                    "mean",


                    "real_volume":
                    "sum"

                }

            )

            .dropna()

            .reset_index()

        )



        #
        # IMPORTANT
        #
        # remove current incomplete H1 candle
        #

        h1 = h1.iloc[:-1]



        return h1



    except Exception as e:


        log(
            f"ERROR | H1 builder failed {e}"
        )


        return None