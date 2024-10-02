const redisClient = require('../config/redis.config.js');
const { promisify } = require('util');
const  Submission  = require('../models/submission.model.js');
const { validationResult } = require('express-validator');

// Promisify Redis `lpush` for enqueuing submission data
const lpushAsync = promisify(redisClient.lpush).bind(redisClient);

const runSubmitProblem = async (req, res) => {
    const { user_id, problem_id, code, language, action } = req.body;
    let submission = null;
    try {
        // Create an entry in the database
        submission = new Submission({
            problem_id: problem_id,
            user_id: user_id,
            code,
            language,
            status: 'pending',
            action,
            createdAt: new Date(),
            updatedAt: new Date(),
        });
        await submission.save();

        console.log(`Submission stored with submissionId: ${submission.submission_id}, action: ${action}`);

        // Prepare submission data for Redis queue
        const submissionData = {
            submissionId: submission.submission_id,
            problem_id,
            code,
            language,
            action,  // 'RUN' or 'SUBMIT'
            timestamp: new Date().toISOString(),
        };

        // Push submission data to the appropriate Redis queue
        const queue = action === 'RUN' ? 'runQueue' : 'submitQueue';
        await lpushAsync(queue, JSON.stringify(submissionData));
        console.log(`Submission enqueued with submissionId : ${submission.submission_id} to ${queue}`);
                        
        // Respond immediately to the frontend
        res.status(200).json({
            message: `${action} request enqueued successfully.`,
            submissionId: submission.submission_id,
        });
    }
    catch(error) {
        console.error(`Error processing ${action} request:`, error);
        res.status(500).json({ error: `Failed to ${action.toLowerCase()} the code.` });
    }
};

module.exports = { runSubmitProblem };
