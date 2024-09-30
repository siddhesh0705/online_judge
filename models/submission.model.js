const { DataTypes } = require('sequelize');
const db = require('../config/db.config.js');

const Submission = db.define('Submission', {    
        submission_id: {
            type: DataTypes.INTEGER,
            autoIncrement: true,
            primaryKey: true
        },
        problem_id: {
            type: DataTypes.INTEGER,
            allowNull: false,
            references: {
                model: 'problems',
                key: 'problem_id'
            }
        },
        code: {
            type: DataTypes.TEXT,
            allowNull: false
        },
        language: {
            type: DataTypes.STRING,
            allowNull: false,
        },
        results: {
            type: DataTypes.JSONB,
        },
        status: {
            type: DataTypes.STRING,
            allowNull: false,
            defaultValue: 'pending'
        },
    }, {
        tableName: 'submissions',
        timestamps: true,
});

module.exports = Submission;