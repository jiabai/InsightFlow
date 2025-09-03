from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_validator

class FileMetadataResponse(BaseModel):
    """
    Pydantic model for file metadata response.
    
    This model defines the structure of file metadata that is returned by the API endpoints.
    It includes essential file information such as ID, name, size, type and timestamps.
    
    Attributes:
        id (int): Database record ID
        file_id (str): Unique file identifier
        user_id (str): ID of the user who owns the file
        filename (str): Original name of the file
        file_size (int): Size of the file in bytes
        file_type (Optional[str]): MIME type of the file
        upload_time (str): ISO formatted timestamp of when the file is uploaded
        stored_filename (str): Name under which the file is stored in the system
    """
    id: int
    file_id: str
    user_id: str
    filename: str
    file_size: int
    file_type: Optional[str] = None
    upload_time: str
    stored_filename: str

    class Config:
        """
        Configuration class for FileMetadataResponse model.
        
        This class enables ORM mode by setting from_attributes=True, allowing the model
        to work directly with SQLAlchemy ORM objects by automatically mapping 
        attributes from the ORM instance to the Pydantic model fields.
        """
        from_attributes = True

    @field_validator("upload_time", mode="before")
    @classmethod
    def format_upload_time(cls, value):
        """
        Format the upload time value to ISO format string.

        This validator ensures that datetime objects are converted to ISO format strings
        for consistent representation in API responses.

        Args:
            cls: The class reference (automatically provided by Pydantic)
            value: The upload time value to format, can be datetime or string

        Returns:
            str: The upload time in ISO format string
        """
        if isinstance(value, datetime):
            return value.isoformat()
        return value
