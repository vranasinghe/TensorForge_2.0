"""Disable network connections in-process, then load and call the real model."""
import socket
from app.predictor import Predictor
from app.schemas import ROOT, validate


def forbidden(*args, **kwargs):
    raise AssertionError('Inference attempted a network connection')


def main():
    original=socket.socket.connect
    socket.socket.connect=forbidden
    try:
        predictor=Predictor(ROOT/'artifacts')
        for text in ('My food is late.', 'මගේ බෑග් එක අමතක වුණා', 'என் உணவு வரவில்லை', 'mage order late', 'en order varala', 'order එක late', '🍔'):
            validate('PredictResponse',predictor.predict_one({'channel':'chat','text':text}))
        print('Offline in-process model load and 7 multilingual predictions passed.')
    finally:
        socket.socket.connect=original


if __name__=='__main__':
    main()
