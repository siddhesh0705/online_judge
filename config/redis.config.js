const Redis = require("ioredis");

const redisClient = new Redis({
    host: process.env.REDIS_HOST,
    port: process.env.REDIS_PORT,
});

redisClient.on('error', (err) => {
    console.log('Redis Client Error', err);
})

redisClient.on('connect', () => {
    console.log('Connected to Redis');
});

const { promisify } = require('util');
redisClient.lpushAsync = promisify(redisClient.lpush).bind(redisClient);
redisClient.lpopAsync = promisify(redisClient.lpop).bind(redisClient);

module.exports = redisClient;