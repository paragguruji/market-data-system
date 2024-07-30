

def test_simple_log(log_stream, string_logger):
    log_stream.truncate(0)
    log_stream.seek(0)
    string_logger.extra = {"context_id": 1234}
    string_logger.info("log 1", key=2)
    expected = "level=INFO logger=string_logger event=\"log 1\" key=\"2\" context_id=\"1234\"\n"
    assert log_stream.getvalue() == expected


def test_error_log(log_stream, string_logger):
    log_stream.truncate(0)
    log_stream.seek(0)
    string_logger.extra = dict()
    try:
        try:
            raise KeyError("inner error")
        except KeyError as e:
            raise ValueError("outer error") from e
    except ValueError:
        string_logger.error("found errors", nesting=2)
    actual = log_stream.getvalue()
    assert actual.startswith(
        'level=ERROR logger=string_logger event="found errors" nesting="2" error_type="ValueError" '
        'error_message="outer error"\nTraceback (most recent call last):')
    assert ' raise KeyError("inner error")' in actual
    assert ' raise ValueError("outer error") from e' in actual
    assert '\nKeyError: \'inner error\'\n' in actual
    assert '\nValueError: outer error\n' in actual

