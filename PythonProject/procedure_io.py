import yaml
import pandas as pd
import os


def load_config(file_name='config.yaml'):
    with open(file_name, encoding='utf-8') as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config

def save_data(results, subject_id, start_time, path="results"):
    os.makedirs(path, exist_ok=True)
    if not str(subject_id).strip():
        subject_id = "unknown"

    file_name = f"subject_{subject_id}_{start_time}.csv"
    df = pd.DataFrame(results)
    df.to_csv(os.path.join(path, file_name), index=False)