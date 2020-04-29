import tensorflow as tf
import datetime

# Tensorboard checkpoints:
log_dir = "logs/fit/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
train_gen_log_dir = 'logs/gradient_tape/' + current_time + '/gen_train'
train_disc_log_dir = 'logs/gradient_tape/' + current_time + '/gen_train'
gen_summary_writer = tf.summary.create_file_writer(train_gen_log_dir)
disc_summary_writer = tf.summary.create_file_writer(train_disc_log_dir)

discriminative_net = tf.keras.Sequential(
      [
          tf.keras.layers.InputLayer(input_shape=(28, 28,  1)),
          tf.keras.layers.Conv2D(filters=64, kernel_size=5, strides=(2, 2), padding="SAME"),
          tf.keras.layers.LeakyReLU(),
          tf.keras.layers.Dropout(0.3),
          tf.keras.layers.Conv2D(filters=128, kernel_size=5, strides=(2, 2), padding="SAME"),
          tf.keras.layers.LeakyReLU(),
          tf.keras.layers.Dropout(0.3),
          tf.keras.layers.Flatten(),
          tf.keras.layers.Dense(1)
      ]
    )
generative_net = tf.keras.Sequential(
    [
        tf.keras.layers.InputLayer(input_shape=(100,)),
        tf.keras.layers.Dense(7*7*128),
        tf.keras.layers.Reshape((7, 7, 128)),
        tf.keras.layers.Conv2DTranspose(filters=64, kernel_size=5, strides=(2, 2), padding="SAME"),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.LeakyReLU(),
        tf.keras.layers.Conv2DTranspose(filters=28, kernel_size=5, strides=(2, 2), padding="SAME"),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.LeakyReLU(),
        tf.keras.layers.Conv2DTranspose(filters=1, kernel_size=4, strides=(1, 1), padding="SAME", activation='tanh'),
    ]
)

# Discriminative_net outputs has no "activation" --> from_logits = true:
cross_entropy = tf.keras.losses.BinaryCrossentropy(from_logits=True)


# Use loss as well proposed by google tf:
def discriminator_loss(real_output, fake_output):
    # tf.ones_like returns same tensor shape as real output but with ones
    # tf.zeros_like returns same tensor shape as fake output but with zeros
    real_loss = cross_entropy(tf.ones_like(real_output), real_output)
    fake_loss = cross_entropy(tf.zeros_like(fake_output), fake_output)
    total_loss = real_loss + fake_loss
    return total_loss


def generator_loss(fake_output):
    return cross_entropy(tf.ones_like(fake_output), fake_output)


# For first tests, let's use Adam optimizers with defaults hyperparams:
generator_optimizer = tf.keras.optimizers.Adam(1e-4)
discriminator_optimizer = tf.keras.optimizers.Adam(1e-4)


# To finish defining our model, we should create a train_step funct:
# Use of decorator to make tf compute the funct in a graph:
@tf.function
def dcgan_train_step(images, batch_size, noise_dim, epoch):
    # First create a noise to pass through generative model:
    noise = tf.random.normal([batch_size, noise_dim])

    # Then feed forward:
    with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
        # Get a fake image:
        generated_images = generative_net(noise, training=True)
        # Pass a real and a fake image through discriminative_net:
        real_output = discriminative_net(images, training=True)
        fake_output = discriminative_net(generated_images, training=True)
        # Compute loss:
        gen_loss = generator_loss(fake_output)
        disc_loss = discriminator_loss(real_output, fake_output)
        with gen_summary_writer.as_default():
          tf.summary.scalar('gen_loss', gen_loss, step=epoch)
        with disc_summary_writer.as_default():
          tf.summary.scalar('disc_loss', disc_loss, step=epoch)

    # Compute gradients:
    gradients_of_generator = gen_tape.gradient(gen_loss, generative_net.trainable_variables)
    gradients_of_discriminator = disc_tape.gradient(disc_loss, discriminative_net.trainable_variables)

    # Backpropagate:
    generator_optimizer.apply_gradients(zip(gradients_of_generator, generative_net.trainable_variables))
    discriminator_optimizer.apply_gradients(zip(gradients_of_discriminator, discriminative_net.trainable_variables))
