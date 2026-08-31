import pytest
from unittest.mock import MagicMock, patch

from src.transfer.writers.syp_iclow_stamp import (
    ICLOWStampError,
    stamp_on_submit,
    revert_on_cancel,
    mark_received,
)


@pytest.fixture
def mock_engine():
    """Mock SQLAlchemy engine for testing."""
    with patch("src.transfer.writers.syp_iclow_stamp.writer_engine_for_branch") as mock:
        engine = MagicMock()
        mock.return_value = engine
        yield engine


@pytest.fixture
def mock_settings():
    """Mock transfer settings for testing."""
    with patch("src.transfer.writers.syp_iclow_stamp.get_transfer_settings") as mock:
        settings = MagicMock()
        settings.is_syp = True
        mock.return_value = settings
        yield settings


def test_stamp_on_submit_success(mock_engine, mock_settings):
    """Test successful stamping on submit."""
    # Setup
    mock_engine.begin.return_value.__enter__.return_value.execute.side_effect = [
        # First query to find ICLOW record - returns one result
        MagicMock(mappings=lambda: MagicMock(first=lambda: {"ID": "iclow123"})),
        # Second query for update 
        MagicMock()
    ]
    
    # Execute
    result = stamp_on_submit(bcode="TEST001", short_id="abc123")
    
    # Verify
    assert result["iclow_id"] == "iclow123"
    assert result["bcode"] == "TEST001"


def test_stamp_on_submit_no_open_iclow(mock_engine, mock_settings):
    """No open ICLOW row — skip stamp (transfer still valid)."""
    mock_engine.begin.return_value.__enter__.return_value.execute.side_effect = [
        MagicMock(mappings=lambda: MagicMock(first=lambda: None)),
    ]
    assert stamp_on_submit(bcode="TEST001", short_id="abc123") is None


def test_stamp_on_submit_db_error(mock_engine, mock_settings):
    """Test stamping when database update fails."""
    # Setup
    mock_engine.begin.return_value.__enter__.return_value.execute.side_effect = [
        # First query to find ICLOW record - returns one result
        MagicMock(mappings=lambda: MagicMock(first=lambda: {"ID": "iclow123"})),
        # Second query that raises an exception
        Exception("Database error"),
    ]
    
    # Execute and verify
    with pytest.raises(ICLOWStampError) as exc_info:
        stamp_on_submit(bcode="TEST001", short_id="abc123")
    
    assert exc_info.value.code == "iclow_update_failed"


def test_revert_on_cancel_success(mock_engine, mock_settings):
    """Test successful revert on cancel."""
    # Setup
    mock_engine.begin.return_value.__enter__.return_value.execute.return_value = MagicMock()
    
    # Execute
    revert_on_cancel(iclow_id="iclow123")
    
    # Verify
    mock_engine.begin.return_value.__enter__.return_value.execute.assert_called_once()


def test_revert_on_cancel_db_error(mock_engine, mock_settings):
    """Test revert on cancel fails when database update fails."""
    # Setup
    mock_engine.begin.return_value.__enter__.return_value.execute.side_effect = Exception("Database error")
    
    # Execute and verify  
    with pytest.raises(ICLOWStampError) as exc_info:
        revert_on_cancel(iclow_id="iclow123")
    
    assert exc_info.value.code == "iclow_revert_failed"


def test_mark_received_success(mock_engine, mock_settings):
    """Test successful mark received."""
    # Setup
    mock_engine.begin.return_value.__enter__.return_value.execute.return_value = MagicMock()
    
    # Execute
    mark_received(iclow_id="iclow123", tf_billno="BILL123456789012")
    
    # Verify
    mock_engine.begin.return_value.__enter__.return_value.execute.assert_called_once()


def test_mark_received_db_error(mock_engine, mock_settings):
    """Test mark received fails when database update fails."""
    # Setup
    mock_engine.begin.return_value.__enter__.return_value.execute.side_effect = Exception("Database error")
    
    # Execute and verify  
    with pytest.raises(ICLOWStampError) as exc_info:
        mark_received(iclow_id="iclow123", tf_billno="BILL123456789012")
    
    assert exc_info.value.code == "iclow_receive_failed"


def test_not_syp_site_raises_error(mock_settings):
    """Test that SYP-only operations fail when not on SYP site."""
    # Setup
    mock_settings.is_syp = False
    
    # Execute and verify 
    with pytest.raises(ICLOWStampError) as exc_info:
        stamp_on_submit(bcode="TEST001", short_id="abc123")
    
    assert exc_info.value.code == "not_syp_site"