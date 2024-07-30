from pytest_mock.plugin import MockerFixture

from app import main


def test_main(mocker: MockerFixture):
    sys_argv = mocker.patch("sys.argv")
    sys_argv.return_value = ["config_path"]
    config_patch = mocker.patch("app.load_market_data_system_config")
    service_patch = mocker.patch("app.MarketDataService")

    service_patch.return_value.run = mocker.MagicMock()
    assert not config_patch.called
    assert not service_patch.called
    assert not service_patch.return_value.run.called
    main()
    assert config_patch.call_count == 1
    assert service_patch.call_count == 1
    assert service_patch.return_value.run.call_count == 1
