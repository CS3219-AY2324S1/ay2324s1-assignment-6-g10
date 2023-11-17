FROM node:18.18-alpine
WORKDIR /src/serverless-g10
COPY package.json .
COPY ./serverless.yml .
COPY package*.json .
COPY codeforces.py .
RUN npm install
RUN npm install -g serverless
EXPOSE 3000
CMD ["serverless", "offline"]