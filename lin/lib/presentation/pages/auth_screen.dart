import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../presentation/providers/auth_provider.dart';

/// Authentication screen for Sign In / Sign Up
class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  void _handleSignIn() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text;

    if (email.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all fields')),
      );
      return;
    }

    try {
      await ref.read(authNotifierProvider.notifier).signin(
        email: email,
        password: password,
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Sign in failed: ${e.toString()}')),
        );
      }
    }
  }

  void _handleSignUp() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    final confirmPassword = _confirmPasswordController.text;

    if (email.isEmpty || password.isEmpty || confirmPassword.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all fields')),
      );
      return;
    }

    if (password != confirmPassword) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Passwords do not match')),
      );
      return;
    }

    try {
      await ref.read(authNotifierProvider.notifier).signup(
        email: email,
        password: password,
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Sign up failed: ${e.toString()}')),
        );
      }
    }
  }

  void _handleDemoSignin() async {
    try {
      await ref.read(authNotifierProvider.notifier).demoSignin();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Demo sign in failed: ${e.toString()}')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authNotifierProvider);

    return Scaffold(
      body: Stack(
        children: [
          // Background gradient
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  AppTheme.primaryColor.withValues(alpha: 0.1),
                  AppTheme.secondaryColor.withValues(alpha: 0.05),
                ],
              ),
            ),
          ),
          SafeArea(
            child: SingleChildScrollView(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    const SizedBox(height: 40),
                    // App logo and title
                    Icon(
                      Icons.link,
                      size: 80,
                      color: AppTheme.primaryColor,
                    ),
                    const SizedBox(height: 24),
                    Text(
                      'Linkd',
                      style: Theme.of(context).textTheme.displayMedium?.copyWith(
                        color: AppTheme.primaryColor,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Professional Networking Intelligence',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppTheme.textSecondary,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 48),
                    // Tab bar
                    TabBar(
                      controller: _tabController,
                      labelColor: AppTheme.primaryColor,
                      unselectedLabelColor: AppTheme.textSecondary,
                      indicatorColor: AppTheme.primaryColor,
                      indicatorWeight: 3,
                      tabs: const [
                        Tab(text: 'Sign In'),
                        Tab(text: 'Sign Up'),
                      ],
                    ),
                    const SizedBox(height: 32),
                    // Tab content
                    SizedBox(
                      height: 350,
                      child: TabBarView(
                        controller: _tabController,
                        children: [
                          // Sign In Tab
                          _buildSignInForm(context, authState),
                          // Sign Up Tab
                          _buildSignUpForm(context, authState),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),
                    // Demo sign in button
                    Column(
                      children: [
                        Text(
                          'Or try demo',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppTheme.textSecondary,
                          ),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: authState.isLoading ? null : _handleDemoSignin,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.green.shade600,
                              padding: const EdgeInsets.symmetric(vertical: 12),
                            ),
                            child: authState.isLoading
                                ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation(Colors.white),
                              ),
                            )
                                : Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Icon(Icons.rocket_launch, size: 20),
                                const SizedBox(width: 8),
                                const Text('Quick Demo Access'),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSignInForm(BuildContext context, AuthState authState) {
    return Column(
      children: [
        TextField(
          controller: _emailController,
          decoration: InputDecoration(
            hintText: 'Email',
            prefixIcon: const Icon(Icons.email),
          ),
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _passwordController,
          decoration: InputDecoration(
            hintText: 'Password',
            prefixIcon: const Icon(Icons.lock),
          ),
          obscureText: true,
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: authState.isLoading ? null : _handleSignIn,
            child: authState.isLoading
                ? const SizedBox(
                  height: 20,
                  width: 20,
                  child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation(Colors.white)),
                )
                : const Text('Sign In'),
          ),
        ),
      ],
    );
  }

  Widget _buildSignUpForm(BuildContext context, AuthState authState) {
    return Column(
      children: [
        TextField(
          controller: _emailController,
          decoration: InputDecoration(
            hintText: 'Email',
            prefixIcon: const Icon(Icons.email),
          ),
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _passwordController,
          decoration: InputDecoration(
            hintText: 'Password',
            prefixIcon: const Icon(Icons.lock),
          ),
          obscureText: true,
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _confirmPasswordController,
          decoration: InputDecoration(
            hintText: 'Confirm Password',
            prefixIcon: const Icon(Icons.lock_outline),
          ),
          obscureText: true,
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: authState.isLoading ? null : _handleSignUp,
            child: authState.isLoading
                ? const SizedBox(
                  height: 20,
                  width: 20,
                  child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation(Colors.white)),
                )
                : const Text('Sign Up'),
          ),
        ),
      ],
    );
  }
}
