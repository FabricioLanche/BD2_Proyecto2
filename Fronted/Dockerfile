FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
ENV VITE_API_PROXY=http://host.docker.internal:8000
CMD ["npm", "run", "dev"]
