"""Excel Loader for processing .xlsx and .xls files from URLs or local paths."""

import requests
import pandas as pd
import tempfile
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from service.log_helper import LogHelper
import config

logger = LogHelper.get_logger("ExcelLoader")


class ExcelLoader:
    """
    Loads Excel files from URLs or local file paths and converts them to text documents.
    Each sheet becomes a separate document with structured text representation.
    """

    def __init__(self, url_or_path: str, sheet_names: Optional[List[str]] = None):
        """
        Initialize ExcelLoader.
        
        Args:
            url_or_path: URL to Excel file or local file path
            sheet_names: Specific sheet names to load (None = all sheets)
        """
        self.url_or_path = url_or_path
        self.sheet_names = sheet_names
        self.is_url = url_or_path.startswith(('http://', 'https://'))

    def load(self) -> List[Document]:
        """Load Excel file and return list of Document objects."""
        try:
            if self.is_url:
                return self._load_from_url()
            else:
                return self._load_from_file()
        except Exception as e:
            logger.error(f"Failed to load Excel file {self.url_or_path}: {e}")
            return []

    def _load_from_url(self) -> List[Document]:
        """Download Excel file from URL and process it."""
        try:
            logger.info(f"Downloading Excel file from: {self.url_or_path}")
            
            # Download the file
            response = requests.get(self.url_or_path, timeout=30)
            response.raise_for_status()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            # Load from temporary file
            docs = self._load_from_file(temp_path)
            
            # Add URL metadata to all documents
            for doc in docs:
                doc.metadata['url'] = self.url_or_path
                doc.metadata['source_type'] = 'excel_url'
            
            return docs
            
        except requests.RequestException as e:
            logger.error(f"Failed to download Excel file from {self.url_or_path}: {e}")
            return []

    def _load_from_file(self, file_path: Optional[str] = None) -> List[Document]:
        """Load Excel file from local path."""
        path = file_path or self.url_or_path
        
        try:
            logger.info(f"Loading Excel file: {path}")
            
            # Read Excel file with all sheets
            excel_data = pd.read_excel(path, sheet_name=None, engine='openpyxl')
            
            # Filter sheets if specific names provided
            if self.sheet_names:
                excel_data = {name: df for name, df in excel_data.items() 
                             if name in self.sheet_names}
            
            documents = []
            
            for sheet_name, df in excel_data.items():
                # Skip empty sheets
                if df.empty:
                    logger.warning(f"Skipping empty sheet: {sheet_name}")
                    continue
                
                # Convert DataFrame to structured text
                text_content = self._dataframe_to_text(df, sheet_name)
                
                # Create metadata
                metadata = {
                    'source': path,
                    'sheet_name': sheet_name,
                    'rows': len(df),
                    'columns': len(df.columns),
                    'source_type': 'excel_file',
                    'title': f"Excel: {sheet_name}"
                }
                
                # Add URL if this was loaded from URL
                if self.is_url:
                    metadata['url'] = self.url_or_path
                    metadata['source_type'] = 'excel_url'
                
                documents.append(Document(
                    page_content=text_content,
                    metadata=metadata
                ))
                
                logger.info(f"Processed sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} columns")
            
            logger.info(f"Successfully loaded {len(documents)} sheets from Excel file")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to process Excel file {path}: {e}")
            return []

    def _dataframe_to_text(self, df: pd.DataFrame, sheet_name: str) -> str:
        """Convert DataFrame to structured text representation."""
        lines = []
        lines.append(f"=== EXCEL SHEET: {sheet_name} ===")
        lines.append(f"Rows: {len(df)}, Columns: {len(df.columns)}")
        lines.append("")
        
        # Add column headers
        lines.append("COLUMNS:")
        for i, col in enumerate(df.columns, 1):
            lines.append(f"{i}. {col}")
        lines.append("")
        
        # Add data rows
        lines.append("DATA:")
        for row_num, (idx, row) in enumerate(df.iterrows(), 1):
            row_data = []
            for col in df.columns:
                value = row[col]
                # Handle NaN values
                # Explicitly convert to bool for static type checkers
                if bool(pd.isna(value)):
                    value = "[EMPTY]"
                else:
                    value = str(value).strip()
                row_data.append(f"{col}: {value}")
            
            lines.append(f"Row {row_num}: {' | '.join(row_data)}")
            
            # Limit number of rows to prevent huge documents
            if row_num >= config.EXCEL_MAX_ROWS_PER_SHEET:
                lines.append(f"... [TRUNCATED - showing first {config.EXCEL_MAX_ROWS_PER_SHEET} of {len(df)} rows]")
                break
        
        return "\n".join(lines)


def load_excel_from_url(url: str, sheet_names: Optional[List[str]] = None) -> List[Document]:
    """Convenience function to load Excel file from URL."""
    return ExcelLoader(url, sheet_names).load()


def load_excel_from_file(file_path: str, sheet_names: Optional[List[str]] = None) -> List[Document]:
    """Convenience function to load Excel file from local path."""
    return ExcelLoader(file_path, sheet_names).load()