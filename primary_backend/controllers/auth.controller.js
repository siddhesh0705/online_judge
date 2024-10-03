const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const cookie=require('cookie-parser');
const User = require('../models/user.model.js');
require('dotenv').config();

const register = async (req, res) => {
    try {
        const { email, password } = req.body;

        if(!email || !password){
            return res.status(400).json({ message : 'Email and Password are required' });
        }

        const existingUser = await User.findOne( { where : { email } });

        if (existingUser) {
            return res.status(400).json({ message: 'User already exists!' });
        }

        const hashedPassword = await bcrypt.hash(password, 10);
        const newUser = new User({
            email,
            password: hashedPassword
        });
        await newUser.save();

        res.status(201).json({ message: 'User registered successfully' });
    }
    catch(error) {
        res.status(500).json({ message: 'Server error' });
    }
};


const login = async (req, res) => {
    try {
        const { email, password } = req.body;

        if (!email || !password) {
            return res.status(400).json({ message: 'Email and password are required.' });
        }
       
        const checkUser = await User.findOne({ where: { email } });
        if (!checkUser) {
            return res.status(400).json({ message: 'Email is not registered.' });
        }
        
        const comparePassword = await bcrypt.compare(password, checkUser.password);
        if (!comparePassword) {
            return res.status(400).json({ message: 'Wrong Password.' });
        }

        let token = jwt.sign({ email, user_id: checkUser.user_id }, process.env.JWT_SECRET); // secret key shouldnt be leaked
        res.cookie("token", token, { httpOnly: true, secure: process.env.NODE_ENV === 'production' });
        res.status(200).json({ message: 'Login Successful' });
    }
    catch (error) {
        return res.status(500).json({ message: 'Server Error'});
    }
};


const logout = (req, res) => {  
    try {
        if (!req.cookies.token) {
            return res.status(401).json({ message: 'Already logged out' });
        }
        res.clearCookie("token", { httpOnly: true, secure: process.env.NODE_ENV === 'production' });
        res.status(200).json({ message : 'Logout Successful' });
    }
    catch (error) {
        return res.status(500).json({ message: 'Server error' });
    }
}


module.exports = {
    register,
    login,
    logout
};
