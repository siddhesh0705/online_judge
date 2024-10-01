const { Sequelize } = require('sequelize');
require('dotenv').config();

const { DATABASE_PORT, DATABASE_USERNAME, DATABASE_NAME, DATABASE_PASSWORD, DATABASE_HOST } = process.env;

// Initialize Sequelize
const db = new Sequelize(DATABASE_NAME, DATABASE_USERNAME, DATABASE_PASSWORD, {
    host: DATABASE_HOST,
    port: DATABASE_PORT,
    dialect: 'postgres',
    protocol: 'postgres',
    logging: false,
});

// Database connection
const testConnection = async () => {
    try {
        await db.authenticate();
        console.log('Database connection has been established successfully.');
    } catch (error) {
        console.error('Unable to connect to the database:', error);
    }
};

testConnection();

// Import Models
const Problem = require('../models/problem.model.js');
const Submission = require('../models/submission.model.js');
const User = require('../models/user.model.js');

// Relations
Submission.belongsTo(Problem, { foreignKey: 'problem_id' });
Submission.belongsTo(User, { foreignKey: 'user_id' });

Problem.hasMany(Submission, { foreignKey: 'problem_id' });
User.hasMany(Submission, { foreignKey: 'user_id' });

// Export the Sequelize instance and models
module.exports = {
    db,
    Problem,
    Submission,
    User,
};
