import sys
from src.scripts.scoring.extract.extract_data import extract_scoring_data
from src.scripts.scoring.transform.transform_data import main_transform_data
from src.scripts.scoring.load.to_postgres import load_data_to_postgres
from src.scripts.scoring.load.to_minio import load_data_to_minio
from src.scripts.utils import common as utils

    
def main_scoring(scoring_month):
    # Extract data
    df = extract_scoring_data(scoring_month)
    
    # Transform data
    df = main_transform_data(df, scoring_month=scoring_month)
    # Load data
    load_data_to_minio(df, scoring_month=scoring_month)
    load_data_to_postgres(df)

if __name__ == "__main__":
    # get arguments
    args_string = " ".join(sys.argv[1:])
    args = utils.process_args_to_dict(args_string)
    scoring_month = args["dt_to"][:6]
    
    main_scoring(scoring_month)