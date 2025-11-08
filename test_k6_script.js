import http from 'k6/http';

import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '5s', target: 100 },
    { duration: '30s', target: 100 },
    { duration: '1s', target: 0 }
  ],
  vusMax: 100,
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
    checks: ['rate>0.99']
  }
};

export default function() {
  const url = 'https://quickpizza.grafana.com';
  const response = http.get(url);
  
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500
  });
  
  sleep(Math.random() * 2 + 1);
}

