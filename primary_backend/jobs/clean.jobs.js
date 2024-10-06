const cron = require('node-cron');
const { Submission } = require('../models/submission.model.js');

const startCleanupJob = () => {
    const job = cron.schedule('*/30 * * * *', async () => { // every half hour
        try {
            console.log('Cron Job: Starting cleanup of completed RUN submissions...');

            const deletedCount = await Submission.destroy({
                where: {
                    action: 'RUN',
                    status: {
                        [Submission.sequelize.Op.ne]: 'pending',
                    },
                },
            });

            console.log(`Cron Job: Deleted ${deletedCount} completed RUN submissions.`);
        }
        catch(error) {
            console.error('Cron Job: Failed to clean up completed RUN submissions.', error.message);

            // Stop the job after logging the error
            console.log('Cron Job: Stopping cleanup job to prevent further failures.');
            job.stop();  // Stop the cron job to prevent retries and issues
        }
    }, {
        scheduled: true,  // Ensures the job starts and runs on schedule
    });

    console.log('Cleanup cron job started and scheduled to run every 30 minutes.');
};

module.exports = { startCleanupJob };
