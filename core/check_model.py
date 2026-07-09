import joblib

model = joblib.load(
    "model/trading_model.pkl"
)

print(type(model))


if isinstance(model, dict):

    for k,v in model.items():

        print(k)
        print(type(v))