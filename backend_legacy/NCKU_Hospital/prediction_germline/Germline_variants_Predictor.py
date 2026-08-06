import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score


class ModelPredictor:
    def __init__(self, model_output_dir):
        self.model_output_dir = model_output_dir
        self.models = self.load_models()
        self.scaler = self.load_scaler()

    def load_models(self):
        # Load all pre-trained models from the specified directory
        models = {}
        model_names = [
            "LogisticRegression",
            # "DecisionTreeClassifier",
            # "RandomForestClassifier",
            # "GradientBoostingClassifier",
            # "AdaBoostClassifier",
            "ExtraTreesClassifier",
            "KNeighborsClassifier",
            # "BalancedBaggingClassifier",
            # "BalancedRandomForestClassifier",
            # "RUSBoostClassifier",
            # "EasyEnsembleClassifier",
            # "XGBClassifier",
            # "LGBMClassifier"
        ]
        for model_name in model_names:
            try:
                model_path = f"{self.model_output_dir}/{model_name}.joblib"
                models[model_name] = joblib.load(model_path)
                print(f"Loaded model: {model_name}")
            except FileNotFoundError:
                print(f"Model not found: {model_name}")
        return models

    def load_scaler(self):
        # Load the pre-trained MinMaxScaler
        scaler_path = f"{self.model_output_dir}/scaler.joblib"
        try:
            scaler = joblib.load(scaler_path)
            print(f"Loaded scaler from: {scaler_path}")
            return scaler
        except FileNotFoundError:
            raise FileNotFoundError(f"Scaler file not found at {scaler_path}")

    def process_TaiwanBioBank(self, df):
        """
        Extract the AF values from the TaiwanBioBank column.
        If the format is not valid or the value is NaN, replace it with 0.
        """
        def extract_af(value):
            if pd.notna(value) and "AF:" in value:
                try:
                    return float(value.split("AF:")[-1])
                except ValueError:
                    return 0
            return 0

        df["TaiwanBioBank"] = df["TaiwanBioBank"].apply(extract_af)
        

        return df

    def process_CLNSIG(self, df):
        """
        Process the CLNSIG column and update is_pathogenic and is_benign columns.
        """
        def classify_clnsig(value):
            benign_terms = ["Benign", "Likely_benign", "Benign/Likely_benign"]
            pathogenic_terms = ["Pathogenic", "Likely_pathogenic", "Pathogenic/Likely_pathogenic"]

            if pd.notna(value):
                if value in benign_terms:
                    return 0, 1
                elif value in pathogenic_terms:
                    return 1, 0
            return 0, 0

        df[["is_pathogenic", "is_benign"]] = df["CLNSIG"].apply(classify_clnsig).apply(pd.Series)

        return df

    def preprocess_data(self, df):
        
        selected_columns = [
        "Chr", "Start", "End", "Ref", "Alt", "DP", "VAF", "AF", "AF_eas", "AF_popmax",
        "TaiwanBioBank", "is_pathogenic", "is_benign", "Occurence", 
        "CntSampleWithVariant","FreqConfirmedGermline", "FreqConfirmedSomatic",
        "CLNSIG",
        ]

        df = df[selected_columns].copy()
        # Replace "." with NaN
        df = df.replace(".", np.nan)

        
        df["DP"] = pd.to_numeric(df["DP"], errors="coerce")
        df["VAF"] = pd.to_numeric(df["VAF"], errors="coerce")

        # Process TaiwanBioBank column
        df = self.process_TaiwanBioBank(df)

        # Process CLNSIG column
        df = self.process_CLNSIG(df)

        # Specify numeric columns
        numeric_cols = ["AF", "AF_eas", "AF_popmax", "TaiwanBioBank", "CntSampleWithVariant", "FreqConfirmedGermline", "FreqConfirmedSomatic"]

        # Convert numeric columns to float, handling scientific notation like 3.19e-05
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Fill missing numeric values with 0
        df[numeric_cols] = df[numeric_cols].fillna(0)

        # Process Occurence column
        if "Occurence" in df.columns:
            occurence_cols = ["Occurence_GYN", "Occurence_LGI", "Occurence_NHL", "Occurence_OTH", "Occurence_UGI", "None_Occurence"]
            for col in occurence_cols:
                df[col] = 0

            df = df.apply(self.expand_occurence, axis=1)

        return df

    def expand_occurence(self, row):
        # Columns to create
        occurence_cols = ["Occurence_GYN", "Occurence_LGI", "Occurence_NHL", "Occurence_OTH", "Occurence_UGI", "None_Occurence"]

        try:
            for col in occurence_cols:
                row[col] = 0

            if pd.notna(row["Occurence"]):
                details = {
                    item.split("(")[1].strip(")"): int(item.split("(")[0])
                    for item in row["Occurence"].split(",")
                }

                for key, value in details.items():
                    col_name = f"Occurence_{key}"
                    if col_name in row.index:
                        row[col_name] = value

                # Set None_Occurence to 0 if there are values in Occurence
                row["None_Occurence"] = 0
            else:
                # If Occurence is empty, set None_Occurence to 1
                row["None_Occurence"] = 1

        except Exception as e:
            print(f"Error parsing Occurence for row: {row['Occurence']}, error: {e}")

        return row

    def normalize_data(self, X):
        # Apply the pre-loaded scaler to normalize the data
        X = pd.DataFrame(self.scaler.transform(X), columns=X.columns, index=X.index)
        return X

    # def normalize_data(self, X):
    #     # Identify columns with non-numeric values
    #     non_numeric_cols = {}
    #     for col in X.columns:
    #         non_numeric_values = X[col][~X[col].apply(lambda x: pd.api.types.is_numeric_dtype(type(x)) or pd.isna(x))]
    #         if not non_numeric_values.empty:
    #             non_numeric_cols[col] = non_numeric_values.tolist()

    #     # Log columns with non-numeric values if any
    #     if non_numeric_cols:
    #         print("Columns with non-numeric values and their problematic entries:")
    #         for col, values in non_numeric_cols.items():
    #             print(f"Column: {col}, Non-numeric values: {values}")
    #         raise ValueError("Non-numeric values detected in the input data.")

    #     # Convert columns to numeric
    #     for col in X.columns:
    #         X[col] = pd.to_numeric(X[col], errors="coerce")

    #     # Fill NaN values with 0 after coercion
    #     X = X.fillna(0)

    #     # Apply the pre-loaded scaler to normalize the data
    #     X = pd.DataFrame(self.scaler.transform(X), columns=X.columns, index=X.index)
    #     return X


    def predict(self, input_file):
        # Load input data
        input_data = pd.read_csv(input_file, low_memory=False)

        # Remove rows where DP has the value "-"
        input_data = input_data[input_data["DP"] != "-"]

        Processed_data = self.preprocess_data(input_data)
        # print("Column Names:", Processed_data.columns.tolist())


        # Extract features (ensure to drop non-feature columns)
        X = Processed_data.drop(columns=["Chr", "Start", "End", "Ref", "Alt", "Occurence", "CLNSIG"])

        if X.isnull().any().any():
            nan_columns = X.columns[X.isnull().any()].tolist()
            print(f"Columns with NaN values: {nan_columns}")
            print(f"Number of NaN values in each column:\n{X[nan_columns].isnull().sum()}")
            
        # Normalize features
        X = self.normalize_data(X)

        # Combine predictions from all models using hard voting
        predictions = []

        for model_name, model in self.models.items():
            try:
                pred = model.predict(X)
                predictions.append(pred)
            except Exception as e:
                print(f"Error predicting with model {model_name}: {e}")

        # Convert predictions to a DataFrame
        predictions = np.array(predictions).T

        # Hard voting: Majority vote
        final_predictions = [1 if np.sum(row) > len(row) / 2 else 0 for row in predictions]

        # Add predictions to original input data
        input_data["is_Germline"] = final_predictions

        # Return the updated DataFrame with predictions
        return input_data
    
def run(model_dir, input_file, output_file):
    """
    Run the prediction pipeline with the given parameters.

    Parameters:
        model_output_dir (str): Path to the directory containing the models and scaler.
        input_file (str): Path to the input CSV file.
        output_file (str): Path to the output CSV file to save results.

    Returns:
        None
    """
    predictor = ModelPredictor(model_dir)
    results = predictor.predict(input_file)

    # Save results to CSV
    results.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")

# Example usage
if __name__ == "__main__":
    
    model_output_dir = "/home/cosbi/Predict_germline_variants/Germline_variants_Predictor/models"
    input_file = "/home/cosbi/Predict_germline_variants/Germline_variants_Predictor/merged_result.csv"
    output_file = "/home/cosbi/Predict_germline_variants/Germline_variants_Predictor/merged_result_with_is_Germline.csv"

    run(model_output_dir, input_file, output_file)