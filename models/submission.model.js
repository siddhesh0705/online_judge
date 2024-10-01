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
        },
        onUpdate: 'CASCADE',
        onDelete: 'CASCADE',
    },
    user_id: { // Assuming you have a User model
        type: DataTypes.INTEGER,
        allowNull: false,
        references: {
            model: 'users',
            key: 'user_id'
        },
        onUpdate: 'CASCADE',
        onDelete: 'CASCADE',
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
        allowNull: true,
    },
    action: {
        type: DataTypes.ENUM('RUN', 'SUBMIT'),
        allowNull: false,
    },
    status: {
        type: DataTypes.ENUM('pending', 'accepted', 'wrong_answer', 'time_limit_exceeded', 'memory_limit_exceeded', 'runtime_error', 'compilation_error'),
        allowNull: false,
        defaultValue: 'pending'
    },
}, {
    tableName: 'submissions',
    timestamps: true,
});


Submission.associate = (models) => {
    Submission.belongsTo(models.Problem, { foreignKey: 'problem_id' });
    Submission.belongsTo(models.User, { foreignKey: 'user_id' });
};

module.exports = Submission;
