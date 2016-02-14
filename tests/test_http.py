import requests

import pytest
from mock import MagicMock
from zmon_worker_monitor.builtins.plugins.http import HttpWrapper
from zmon_worker_monitor.zmon_worker.errors import HttpError


def get_dropwizard_metrics():
    # see https://github.com/zalando/connexion/issues/49
    yield {
        'version': '3.0.0',
        'gauges': {},
        'counters': {},
        'histograms': {},
        'meters': {},
        'timers': {
            'zmon.response.200.GET.pets': {
                'count': 1917,
                'max': 1125,
                'mean': 386.16423467091,
                'min': 295,
                'p50': 383,
                'p75': 383,
                'p95': 383,
                'p98': 460,
                'p99': 460,
                'p999': 460,
                'stddev': 15.285876814113,
                'm15_rate': 0.0027894332885165,
                'm1_rate': 3.7570008143941E-5,
                'm5_rate': 0.0016195023085788,
                'mean_rate': 0.0031567415804972,
                'duration_units': 'milliseconds',
                'rate_units': 'calls/second'
            },
            'zmon.response.200.GET.pets.{pet_id}': {
                'count': 392373,
                'max': 627,
                'mean': 219.38202968217,
                'min': 163,
                'p50': 218,
                'p75': 224,
                'p95': 249,
                'p98': 265,
                'p99': 425,
                'p999': 425,
                'stddev': 30.77609293132,
                'm15_rate': 0.69320705677888,
                'm1_rate': 0.67804789230544,
                'm5_rate': 0.71816217263666,
                'mean_rate': 0.64605322610366,
                'duration_units': 'milliseconds',
                'rate_units': 'calls/second'
            }
        }
    }
    # expected
    yield {'pets': {'GET': {'200': {'75th': 383,
                                    '99th': 460,
                                    'count': 1917,
                                    'mRate': 3.7570008143941e-05, 'median': 383, 'min': 295, 'max': 1125,
                                    'mean': 386.16423467091}}},
           'pets.{pet_id}': {'GET': {'200': {'75th': 224,
                                             '99th': 425,
                                             'count': 392373,
                                             'mRate': 0.67804789230544,
                                             'max': 627,
                                             'median': 218,
                                             'min': 163,
                                             'mean': 219.38202968217}}}}


def get_spring_boot_metrics():
    # see https://github.com/zalando/zmon-actuator
    yield {
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.count": 10,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.fifteenMinuteRate": 0.18076110580284566,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.fiveMinuteRate": 0.1518180485219247,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.meanRate": 0.06792011610723951,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.oneMinuteRate": 0.10512398137982051,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.snapshot.75thPercentile": 1173,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.snapshot.95thPercentile": 1233,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.snapshot.98thPercentile": 1282,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.snapshot.999thPercentile": 1282,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.snapshot.99thPercentile": 1282,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.snapshot.max": 1282,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.snapshot.mean": 1170,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.snapshot.median": 1161,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.snapshot.min": 1114,
        "zmon.response.200.GET.rest.api.v1.checks.all-active-check-definitions.snapshot.stdDev": 42,
    }
    # expected
    yield {'rest.api.v1.checks.all-active-check-definitions': {'GET': {'200': {
        'count': 10,
        '75th': 1173,
        '99th': 1282,
        'min': 1114,
        'max': 1282,
        'mRate': 0.10512398137982051,
        'mean': 1170,
        'median': 1161

    }}}}


def get_test_data():
    return [({}, {}),
            tuple(get_dropwizard_metrics()),
            tuple(get_spring_boot_metrics())]


def test_http(monkeypatch):
    resp = MagicMock()
    resp.status_code = 200
    resp.text = '"foo"'
    resp.content = resp.text
    resp.json.return_value = 'foo'
    get = MagicMock()
    get.return_value = resp
    monkeypatch.setattr('requests.get', get)
    http = HttpWrapper('http://example.org')
    assert 200 == http.code()
    assert '"foo"' == http.text()
    assert 'foo' == http.json()
    assert 5 == http.content_size()
    resp.json.side_effect = Exception('JSON fail')
    with pytest.raises(HttpError) as ex:
        http.json()
    assert 'JSON fail' == ex.value.message


def test_http_errors(monkeypatch):
    resp = MagicMock()
    resp.status_code = 404
    resp.raise_for_status.side_effect = requests.HTTPError('Not Found')
    get = MagicMock()
    get.return_value = resp
    monkeypatch.setattr('requests.get', get)
    http = HttpWrapper('http://example.org')
    # the code method will not raise an exception..
    assert 404 == http.code()
    for meth in ('time', 'json', 'cookies', 'headers'):
        with pytest.raises(HttpError) as ex:
            # ..but other methods will!
            getattr(http, meth)()
        assert 'Not Found' == ex.value.message

    get.side_effect = requests.Timeout('timed out')
    http = HttpWrapper('http://example.org')
    with pytest.raises(HttpError) as ex:
        http.time()
    assert 'timeout' == ex.value.message

    get.side_effect = requests.ConnectionError('connfail')
    http = HttpWrapper('http://example.org')
    with pytest.raises(HttpError) as ex:
        http.code()
    assert 'connection failed' == ex.value.message

    get.side_effect = Exception('foofail')
    http = HttpWrapper('http://example.org')
    with pytest.raises(HttpError) as ex:
        http.code()
    assert 'foofail' == ex.value.message


def test_http_actuator_metrics_invalid(monkeypatch):
    resp = MagicMock()
    resp.json.return_value = 'foo'
    get = MagicMock()
    get.return_value = resp
    monkeypatch.setattr('requests.get', get)
    http = HttpWrapper('http://example.org')
    with pytest.raises(HttpError) as ex:
        http.actuator_metrics()
    assert 'Invalid actuator metrics: response must be a JSON object' == ex.value.message


@pytest.mark.parametrize('metrics_response,expected', get_test_data())
def test_http_actuator_metrics_valid(monkeypatch, metrics_response, expected):
    resp = MagicMock()
    resp.json.return_value = metrics_response
    get = MagicMock()
    get.return_value = resp
    monkeypatch.setattr('requests.get', get)
    http = HttpWrapper('http://example.org')
    assert expected == http.actuator_metrics()


def test_http_jolokia(monkeypatch):
    resp = MagicMock()
    resp.json.return_value = {'foo': 'bar'}
    post = MagicMock()
    post.return_value = resp
    monkeypatch.setattr('requests.post', post)
    with pytest.raises(HttpError) as ex:
        http = HttpWrapper('http://example.org/foo')
        http.jolokia([])
    assert 'URL needs to end in jolokia/ and not contain ? and &' == ex.value.message

    http = HttpWrapper('http://example.org/jolokia/')
    assert {'foo': 'bar'} == http.jolokia([{
        "mbean": "java.lang:type=Memory",
        "attribute": "HeapMemoryUsage",
        "path": "used",
    }])


def test_http_prometheus(monkeypatch):
    resp = MagicMock()
    # see http://prometheus.io/docs/instrumenting/exposition_formats/#text-format-details
    resp.text = '''
# HELP api_http_request_count The total number of HTTP requests.
# TYPE api_http_request_count counter
http_request_count{method="post",code="200"} 1027 1395066363000
http_request_count{method="post",code="400"}    3 1395066363000
'''
    get = MagicMock()
    get.return_value = resp
    monkeypatch.setattr('requests.get', get)
    http = HttpWrapper('http://example.org/prometheus/')
    expected = {u'http_request_count': [({u'code': u'200', u'method': u'post'}, 1027.0),
                                        ({u'code': u'400', u'method': u'post'}, 3.0)]}
    assert expected == http.prometheus()