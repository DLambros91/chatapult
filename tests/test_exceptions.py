from chatapult.exceptions import APIError, NetworkError, ConfigurationError
import httpx

def test_apierror_str_repr():
    response = httpx.Response(status_code=404, content=b"Not Found")
    err = APIError("Resource missing", response=response)
    assert str(err) == "[404] Resource missing"
    assert repr(err) == "APIError(message='Resource missing', status_code=404)"

def test_apierror_no_response():
    err = APIError("Some error")
    assert str(err) == "Some error"
    assert repr(err) == "APIError(message='Some error', status_code=None)"

def test_base_errors_str_repr():
    err = NetworkError("Connection lost")
    assert str(err) == "Connection lost"
    assert repr(err) == "NetworkError('Connection lost')"
    
    err2 = ConfigurationError("Invalid key")
    assert str(err2) == "Invalid key"
    assert repr(err2) == "ConfigurationError('Invalid key')"
