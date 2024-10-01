const { DataTypes } = require('sequelize');
const db = require('../config/db.config.js');

const User = db.define('User', {
    user_id: {
        type: DataTypes.INTEGER,
        primaryKey: true,
        autoIncrement: true,
    },
    username: {
        type: DataTypes.STRING,
        allowNull: false,
        unique: true,
        validate: {
            len: {
                args: [3, 25],
                msg: "Username must be between 3 and 25 characters.",
            },
            is: {
                args: /^[a-zA-Z0-9_]+$/i,
                msg: "Username can only contain letters, numbers, and underscores.",
            },
        },
    },
    email: {
        type: DataTypes.STRING,
        allowNull: false,
        unique: true,
        validate: {
            isEmail: {
                msg: "Must be a valid email address.",
            },
        },
    },
    password: {
        type: DataTypes.STRING,
        allowNull: false,
    },
}, {
    tableName: 'users',
    timestamps: true, // Adds createdAt and updatedAt fields
});

module.exports = User;
