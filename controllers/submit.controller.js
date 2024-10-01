const Submission = require('../models/submission.model.js');
const redisClient = require('../config/redis.config.js');
const { promisify } = require('util');

// Promisify Redis client methods for async operations
const lpushAsync = promisify(redisClient.lpush).bind(redisClient);

const submitProblem = async (req, res) => {
    try {
        const { problemId, code, language, action } = req.body;

        // Validate required fields
        if (!problemId || !code || !language || !action) {
            return res.status(400).json({ error: 'Missing required fields.' });
        }

        // Extract userId from session
        const userId = req.session.user.id;

        // SUBMIT AND RUN
        let submission;
        if (action === 'SUBMIT') {
            submission = await Submission.create({
                problem_id: problemId,
                user_id: userId,
                code,
                language,
                status: 'pending',
            });
        }

        // Add submission to Redis queue
        const submissionData = {
            userId,
            problemId,
            code,
            language,
            action,
            submissionId: submission ? submission.submission_id : null,
        };

        const result = await lpushAsync('submissionQueue', JSON.stringify(submissionData));
        console.log('Data stored in Redis:', result);

        res.status(200).json({ message: 'Submission received', submissionId: submission ? submission.submission_id : null });
    } catch (error) {
        console.error("Error submitting the code:", error);
        res.status(500).json({ error: 'Failed to submit code.' });
    }
};

module.exports = { submitProblem };
