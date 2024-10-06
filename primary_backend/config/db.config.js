const sequelize = require('./sequelize.config.js');

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
  sequelize,
  Problem,
  Submission,
  User,
};