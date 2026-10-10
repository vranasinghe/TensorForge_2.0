#!/bin/sh
set -eu
image="${1:-tensorforge:local}"
docker run --rm --network none --entrypoint python "$image" -c 'from app.predictor import Predictor; from app.schemas import ROOT; p=Predictor(ROOT/"artifacts"); print(p.predict_one({"channel":"chat","text":"Food is late"}))'
