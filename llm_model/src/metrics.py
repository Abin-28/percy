"""Precision / recall / F1 per label, written by hand (no extra libraries)."""


def precision_recall(true_labels: list, predicted: list, labels: list) -> dict:
    result = {}
    for lab in labels:
        tp = sum(1 for t, p in zip(true_labels, predicted) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(true_labels, predicted) if t != lab and p == lab)
        fn = sum(1 for t, p in zip(true_labels, predicted) if t == lab and p != lab)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        result[lab] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    return result


def accuracy(true_labels: list, predicted: list) -> float:
    if not true_labels:
        return 0.0
    return sum(1 for t, p in zip(true_labels, predicted) if t == p) / len(true_labels)
