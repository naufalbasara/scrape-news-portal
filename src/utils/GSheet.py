import warnings
import pygsheets
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


class GSheet():

    # IGNORE PYGSHEET USERWARNING, COMMENT FOR DEBUGGING AND TESTING
    warnings.simplefilter('ignore', UserWarning)

    def __init__(self, spreadsheet_key):
        gc = pygsheets.authorize(service_account_file='client_secret.json')
        self.gsh = gc.open_by_key(spreadsheet_key)

    def open_wks(self, worksheet_name):
        return self.gsh.worksheet_by_title(worksheet_name)

    def to_df(self, wks):
        if type(wks) != pygsheets.worksheet.Worksheet:
            wks = self.gsh.worksheet_by_title(wks)
        return wks.get_as_df(include_tailing_empty_rows=False, include_empty_rows=False, numerize=False)

    def trunc_ins(self, sheet_name, df):
        try:
            wks = self.gsh.worksheet_by_title(sheet_name)
        except pygsheets.WorksheetNotFound:
            wks = self.gsh.add_worksheet(sheet_name)
        df = df.fillna('')
        if df.shape[0] != 0:
            wks.clear()
            wks.rows = df.shape[0]
            wks.set_dataframe(df, (1, 1), fit=False)

    def append_ins(self, sheet_name, df, check_column=None):  # check column is use for special scenario where in gsheet there is formula and to insert value of left side before formula
        if df.shape[0] != 0:
            wks = self.gsh.worksheet_by_title(sheet_name)
            if check_column:
                cells = wks.get_all_values(include_tailing_empty_rows=None, include_tailing_empty=True, returnas='matrix')
                target_df = pd.DataFrame(cells[1:], columns=cells[0])
                check_column_list = [i for i in target_df[check_column] if i != '']
                used_column_length = len(check_column_list)+1
            else:
                cells = wks.get_all_values(include_tailing_empty_rows=None, include_tailing_empty=False, returnas='matrix')
                used_column_length = len(cells)
            cells_w_blank = wks.get_all_values(returnas='matrix')
            max_length = used_column_length+df.shape[0]
            if max_length > len(cells_w_blank):
                wks.rows = max_length
            # Insert into gsheet
            df = df.fillna('')
            wks.set_dataframe(df, (used_column_length+1, 1), fit=False)
            wks.delete_rows(used_column_length+1)
        else:
            print(f'{sheet_name} - no new data to insert')  # temporary, to use raise warning instead