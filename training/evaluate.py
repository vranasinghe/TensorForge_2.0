"""Explicit evaluation definitions; never substitutes for measured predictions."""
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix, log_loss, average_precision_score, precision_recall_fscore_support


def primary_metrics(y, probabilities, classes):
    pred = classes[probabilities.argmax(axis=1)]
    correct = pred == y
    confidence = probabilities.max(axis=1)
    bins = []
    ece = 0.
    for low in np.arange(0., 1., .1):
        mask = (confidence >= low) & ((confidence < low + .1) if low < .9 else (confidence <= 1.))
        if mask.any():
            item = {'low': float(low), 'count': int(mask.sum()), 'confidence': float(confidence[mask].mean()), 'accuracy': float(correct[mask].mean())}
            ece += mask.mean() * abs(item['confidence'] - item['accuracy'])
            bins.append(item)
    onehot = np.array([[int(c == target) for c in classes] for target in y])
    return {'accuracy': accuracy_score(y, pred), 'macro_f1': f1_score(y, pred, average='macro', zero_division=0),
            'weighted_f1': f1_score(y, pred, average='weighted', zero_division=0),
            'per_class': classification_report(y, pred, output_dict=True, zero_division=0),
            'confusion_matrix': confusion_matrix(y, pred, labels=classes).tolist(), 'classes': classes.tolist(),
            'log_loss': log_loss(y, probabilities, labels=classes),
            'brier_sum_over_classes': float(np.mean(np.sum((probabilities - onehot)**2, axis=1))),
            'ece_10_equal_width_bins': float(ece), 'reliability_bins': bins,
            'selective_risk': [{'threshold': t, 'coverage': float((confidence >= t).mean()),
                                'risk': float(1 - correct[confidence >= t].mean()) if (confidence >= t).any() else None} for t in np.arange(0., 1., .05)]}


def binary_metrics(y, scores, threshold):
    pred = scores >= threshold
    precision, recall, f1, _ = precision_recall_fscore_support(y, pred, average='binary', zero_division=0)
    return {'precision': float(precision), 'recall': float(recall), 'f1': float(f1),
            'pr_auc_average_precision': float(average_precision_score(y, scores)) if any(y) else None,
            'threshold': float(threshold), 'positives': int(sum(y)), 'count': len(y)}
