# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Consolidated date parsing utilities for LiteLLM-to-CloudZero data processing."""

import zoneinfo
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Union

from rich.console import Console

console = Console()


class DateParser:
    """Centralized date parsing functionality for consistent date handling across the application."""

    def __init__(self, user_timezone: Optional[str] = None):
        """Initialize DateParser with user timezone.
        
        Args:
            user_timezone: Timezone string (e.g., 'US/Eastern', 'UTC'). Defaults to UTC.
        """
        self.user_timezone = self._parse_timezone(user_timezone)

    def _parse_timezone(self, timezone_str: Optional[str]) -> zoneinfo.ZoneInfo:
        """Parse timezone string to ZoneInfo object.
        
        Args:
            timezone_str: Timezone string or None
            
        Returns:
            ZoneInfo object, defaults to UTC if invalid
        """
        if not timezone_str or timezone_str == 'UTC':
            return timezone.utc

        try:
            return zoneinfo.ZoneInfo(timezone_str)
        except zoneinfo.ZoneInfoNotFoundError:
            console.print(f"[yellow]Warning: Unknown timezone '{timezone_str}', using UTC[/yellow]")
            return timezone.utc

    def parse_date_spec(self, mode: str, date_spec: Optional[str]) -> Optional[dict]:
        """Parse date specification based on mode.
        
        Args:
            mode: Operation mode ('day', 'month', or 'all')
            date_spec: Date string in format DD-MM-YYYY for day mode, MM-YYYY for month mode
            
        Returns:
            Dict with 'start_date', 'end_date', and 'description' keys, or None for 'all' mode
            
        Raises:
            ValueError: If date_spec format is invalid
        """
        now = datetime.now(self.user_timezone)

        if mode == 'day':
            return self._parse_day_spec(date_spec, now)
        elif mode == 'month':
            return self._parse_month_spec(date_spec, now)
        elif mode == 'all':
            return None
        else:
            raise ValueError(f"Invalid mode: {mode}")

    def _parse_day_spec(self, date_spec: Optional[str], now: datetime) -> dict:
        """Parse day specification.
        
        Args:
            date_spec: DD-MM-YYYY format or None for today
            now: Current datetime with timezone
            
        Returns:
            Dict with date range for a single day
        """
        if date_spec:
            try:
                day_obj = datetime.strptime(date_spec, '%d-%m-%Y').replace(tzinfo=self.user_timezone)
                start_date = day_obj.strftime('%Y-%m-%d')
                end_date = start_date
            except ValueError:
                raise ValueError(f"Invalid date format '{date_spec}'. Use DD-MM-YYYY (e.g., 15-01-2024)")
        else:
            start_date = now.strftime('%Y-%m-%d')
            end_date = start_date

        return {'start_date': start_date, 'end_date': end_date, 'description': f"Day: {start_date}"}

    def _parse_month_spec(self, date_spec: Optional[str], now: datetime) -> dict:
        """Parse month specification.
        
        Args:
            date_spec: MM-YYYY format or None for current month
            now: Current datetime with timezone
            
        Returns:
            Dict with date range for entire month
        """
        if date_spec:
            try:
                month_obj = datetime.strptime(date_spec, '%m-%Y').replace(tzinfo=self.user_timezone)
            except ValueError:
                raise ValueError(f"Invalid month format '{date_spec}'. Use MM-YYYY (e.g., 01-2024)")
        else:
            month_obj = now

        # Get first day of month
        start_date = month_obj.strftime('%Y-%m-01')

        # Calculate last day of month
        if month_obj.month == 12:
            next_month = month_obj.replace(year=month_obj.year + 1, month=1, day=1)
        else:
            next_month = month_obj.replace(month=month_obj.month + 1, day=1)
        last_day = (next_month - timedelta(days=1)).day
        end_date = month_obj.strftime(f'%Y-%m-{last_day:02d}')

        month_desc = month_obj.strftime('%B %Y')
        return {'start_date': start_date, 'end_date': end_date, 'description': f"Month: {month_desc}"}

    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string and convert to UTC.
        
        Handles various ISO 8601 formats and assumes user timezone if no timezone info provided.
        
        Args:
            timestamp_str: Timestamp string to parse
            
        Returns:
            datetime object in UTC timezone
            
        Raises:
            ValueError: If timestamp cannot be parsed
        """
        try:
            # Handle various ISO 8601 formats
            if timestamp_str.endswith('Z'):
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            elif any(tz_suffix in timestamp_str for tz_suffix in ['+', '-'] if tz_suffix in timestamp_str[-6:]):
                # Has timezone offset
                dt = datetime.fromisoformat(timestamp_str)
            else:
                # No timezone info - assume user timezone
                dt = datetime.fromisoformat(timestamp_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=self.user_timezone)

            # Convert to UTC
            return dt.astimezone(timezone.utc)

        except Exception as e:
            raise ValueError(f"Could not parse timestamp '{timestamp_str}': {e}")

    def parse_date(self, date_value: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse date from various formats into datetime object.
        
        Handles date strings in YYYY-MM-DD format, ISO 8601 timestamps,
        existing datetime objects, and None values.
        
        Args:
            date_value: Date in string format, datetime object, or None
            
        Returns:
            Parsed datetime object with UTC timezone or None
        """
        if date_value is None:
            return None

        if isinstance(date_value, datetime):
            # Ensure timezone awareness
            if date_value.tzinfo is None:
                return date_value.replace(tzinfo=timezone.utc)
            return date_value.astimezone(timezone.utc)

        if isinstance(date_value, str):
            # Try parsing as date only (YYYY-MM-DD)
            if len(date_value) == 10 and date_value.count('-') == 2:
                try:
                    dt = datetime.strptime(date_value, '%Y-%m-%d')
                    return dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            # Try parsing as full timestamp
            try:
                return self.parse_timestamp(date_value)
            except ValueError:
                return None

        return None


def get_date_range(start_date: str, end_date: str) -> Tuple[datetime, datetime]:
    """Convert date strings to datetime range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Tuple of (start_datetime, end_datetime) with UTC timezone
    """
    start = datetime.strptime(start_date, '%Y-%m-%d').replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
    )
    end = datetime.strptime(end_date, '%Y-%m-%d').replace(
        hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
    )
    return start, end
