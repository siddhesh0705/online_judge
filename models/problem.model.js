const { DataTypes } = require('sequelize');
const db = require('../config/db.config.js')

const Problem = db.define('Problem', {
        problem_id: {
            type: DataTypes.INTEGER,
            primaryKey: true,
            autoIncrement: true,
        },
        problem_name: {
            type: DataTypes.STRING,
            allowNull: false
        },
        description: {
            type: DataTypes.TEXT,
            allowNull: false    
        },
        test_cases_file_path: {
            type: DataTypes.STRING,
            allowNull: true,
        },
        expected_output_file_path: {
            type: DataTypes.STRING,
            allowNull: true,
        }
    }, {
        tableName: 'problems'
});

module.exports = Problem;