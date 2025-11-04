"""
Large Content Handler Utility

Provides utilities for handling large content in API responses to avoid token limits.
Supports chunked reading, pagination, and file downloads for large data.
"""

from typing import Dict, Any, Tuple, Optional
from flask import jsonify, send_file, request, Response
from io import BytesIO
import json


class LargeContentHandler:
    """
    Utility class for handling large content in API responses.

    Provides methods for:
    - Chunked/paginated content reading
    - File downloads from strings
    - Consistent API response formatting
    """

    # Default limits (in characters)
    DEFAULT_CHUNK_SIZE = 25000
    MAX_CHUNK_SIZE = 50000

    @staticmethod
    def create_chunked_response(
        content: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        job_id: Optional[str] = None,
        content_type: str = 'content'
    ) -> Tuple[Response, int]:
        """
        Create a chunked response for large content.

        Args:
            content: The full content string
            offset: Starting position (from request args if None)
            limit: Chunk size (from request args if None)
            job_id: Optional job ID for response metadata
            content_type: Type of content being returned (for response key)

        Returns:
            Tuple of (JSON response, HTTP status code)

        Example:
            response, status = LargeContentHandler.create_chunked_response(
                content=large_script,
                job_id='123',
                content_type='script'
            )
        """
        # Get pagination parameters from request if not provided
        if offset is None:
            try:
                offset = int(request.args.get('offset', 0))
            except ValueError:
                offset = 0

        if limit is None:
            try:
                limit = int(request.args.get('limit', LargeContentHandler.DEFAULT_CHUNK_SIZE))
            except ValueError:
                limit = LargeContentHandler.DEFAULT_CHUNK_SIZE

        # Validate parameters
        if offset < 0:
            offset = 0
        if limit < 1:
            limit = LargeContentHandler.DEFAULT_CHUNK_SIZE
        if limit > LargeContentHandler.MAX_CHUNK_SIZE:
            limit = LargeContentHandler.MAX_CHUNK_SIZE

        # Calculate chunk
        total_length = len(content)
        chunk = content[offset:offset + limit]
        has_more = (offset + len(chunk)) < total_length

        response_data = {
            'success': True,
            'content': chunk,
            'metadata': {
                'offset': offset,
                'limit': limit,
                'chunk_length': len(chunk),
                'total_length': total_length,
                'has_more': has_more,
                'next_offset': offset + len(chunk) if has_more else None
            }
        }

        if job_id:
            response_data['job_id'] = job_id

        return jsonify(response_data), 200

    @staticmethod
    def create_download_response(
        content: str,
        filename: str,
        mimetype: str = 'text/plain'
    ) -> Response:
        """
        Create a file download response from string content.

        Args:
            content: The content to download
            filename: Name for the downloaded file
            mimetype: MIME type of the file

        Returns:
            Flask send_file response

        Example:
            return LargeContentHandler.create_download_response(
                content=script_content,
                filename='script.jsx',
                mimetype='text/plain'
            )
        """
        content_bytes = BytesIO(content.encode('utf-8'))
        return send_file(
            content_bytes,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )

    @staticmethod
    def create_summary_response(
        data: Any,
        job_id: str,
        data_type: str,
        endpoint_path: str
    ) -> Dict[str, Any]:
        """
        Create a summary response for large data without including the full content.

        Args:
            data: The full data object (for calculating size)
            job_id: Job ID for constructing endpoint URL
            data_type: Type of data (e.g., 'stage1_results', 'extendscript')
            endpoint_path: Path to the full data endpoint

        Returns:
            Dictionary with summary information

        Example:
            summary = LargeContentHandler.create_summary_response(
                data=job.stage1_results,
                job_id='123',
                data_type='stage1_results',
                endpoint_path='/api/job/{job_id}/stage1-results'
            )
        """
        has_data = bool(data)
        data_size = 0

        if has_data:
            if isinstance(data, str):
                data_size = len(data)
            else:
                data_size = len(json.dumps(data))

        return {
            'has_data': has_data,
            'data_size': data_size,
            'endpoint': endpoint_path.format(job_id=job_id),
            'supports_chunking': True,
            'parameters': {
                'offset': 'Starting position (default: 0)',
                'limit': f'Chunk size (default: {LargeContentHandler.DEFAULT_CHUNK_SIZE}, max: {LargeContentHandler.MAX_CHUNK_SIZE})',
                'full': 'Set to "true" to get full content (use with caution for large data)'
            }
        }

    @staticmethod
    def should_chunk_content(content: str, threshold: int = 25000) -> bool:
        """
        Determine if content should be chunked based on size.

        Args:
            content: The content to check
            threshold: Size threshold in characters

        Returns:
            True if content should be chunked, False otherwise
        """
        return len(content) > threshold

    @staticmethod
    def get_content_stats(content: Any) -> Dict[str, Any]:
        """
        Get statistics about content size and structure.

        Args:
            content: The content to analyze (string, dict, list, etc.)

        Returns:
            Dictionary with content statistics

        Example:
            stats = LargeContentHandler.get_content_stats(job.stage1_results)
            # Returns: {'size': 45000, 'type': 'dict', 'should_chunk': True}
        """
        content_type = type(content).__name__

        if isinstance(content, str):
            size = len(content)
        else:
            size = len(json.dumps(content))

        return {
            'size': size,
            'type': content_type,
            'should_chunk': LargeContentHandler.should_chunk_content(str(content)),
            'estimated_tokens': size // 4  # Rough estimate: ~4 chars per token
        }
