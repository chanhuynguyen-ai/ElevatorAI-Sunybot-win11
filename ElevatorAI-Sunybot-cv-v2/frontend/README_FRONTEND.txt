Frontend này là phần Vite/React hiện có của project.
- vite.config.js: chạy dev server cổng 5173
- package.json: khai báo React, ReactDOM, React Router và script dev/build/preview
- index.html: root mount cho app React

Bạn chỉ cần nối các API sau từ backend CV:
- GET /api/cv/stream
- GET /api/cv/status
- GET /api/cv/events
- GET /api/cv/density
