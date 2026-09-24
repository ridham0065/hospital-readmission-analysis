"""Task 2 — Logistic regression model predicting 30-day readmission.

Loads every eligible admission (v_eligible_admissions: excludes in-hospital
deaths) with its insurance type and discharge location, labels it 1 if its
HADM_ID appears in v_readmissions_30d (the corrected LEAD()-based 30-day
readmission view) and 0 otherwise, one-hot encodes the two categorical
features, and fits a logistic regression classifier.

Run directly: writes confusion_matrix.png next to this script and prints
the accuracy score, classification report, and top feature coefficients.
"""
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

DB = r"C:\Users\patel\OneDrive\Desktop\readmission_analysis.db"
HERE = r"C:\Users\patel\OneDrive\Desktop\MIMIC-III Project"

conn = sqlite3.connect(DB)

eligible = pd.read_sql_query(
    "SELECT HADM_ID, INSURANCE, DISCHARGE_LOCATION FROM v_eligible_admissions",
    conn,
)
readmitted_ids = pd.read_sql_query("SELECT HADM_ID FROM v_readmissions_30d", conn)["HADM_ID"]
conn.close()

eligible["readmitted_30d"] = eligible["HADM_ID"].isin(readmitted_ids).astype(int)

X_cat = eligible[["INSURANCE", "DISCHARGE_LOCATION"]]
y = eligible["readmitted_30d"]

encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
X_encoded = encoder.fit_transform(X_cat)
feature_names = encoder.get_feature_names_out(["INSURANCE", "DISCHARGE_LOCATION"])
X = pd.DataFrame(X_encoded, columns=feature_names, index=eligible.index)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = LogisticRegression(max_iter=1000, class_weight="balanced")
model.fit(X_train, y_train)

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
report = classification_report(y_test, y_pred, target_names=["Not Readmitted", "Readmitted"])
cm = confusion_matrix(y_test, y_pred)

coefs = pd.Series(model.coef_[0], index=feature_names).sort_values(key=abs, ascending=False)

print(f"Rows: {len(eligible):,}  |  Readmitted: {y.sum():,} ({y.mean() * 100:.2f}%)")
print(f"\nAccuracy: {accuracy:.4f}")
print("\nClassification report:")
print(report)
print("Confusion matrix (rows=actual, cols=predicted, order=[Not Readmitted, Readmitted]):")
print(cm)
print("\nTop 10 feature coefficients (by absolute value):")
print(coefs.head(10).to_string())

disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Not Readmitted", "Readmitted"])
fig, ax = plt.subplots(figsize=(6, 5.5))
disp.plot(ax=ax, cmap="Blues", colorbar=False, values_format=",d")
ax.set_title("30-Day Readmission — Logistic Regression\nConfusion Matrix", fontsize=13, color="#1B2A4A", pad=14)
for text in ax.texts:
    text.set_fontsize(13)
plt.tight_layout()
out_path = f"{HERE}\\confusion_matrix.png"
plt.savefig(out_path, dpi=150)
print(f"\nSaved {out_path}")
